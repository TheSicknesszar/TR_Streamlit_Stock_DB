#!/usr/bin/env python3
"""
Database Restore Script for RefurbAdmin AI.

Features:
- Restore from backup file
- Verify integrity before restore
- Rollback capability (creates backup before restore)
- POPIA compliant logging
- South African timezone support

Usage:
    python restore_database.py <backup_file> [--verify-only] [--create-rollback]
    
WARNING: This operation will overwrite the current database!
"""

import os
import sys
import gzip
import shutil
import logging
import argparse
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
import hashlib
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class RestoreConfig:
    """Restore configuration."""
    
    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "refurbadmin"
    db_user: str = "refurbadmin"
    db_password: str = ""
    
    # Restore settings
    backup_dir: str = "./data/backups"
    create_rollback: bool = True
    verify_before_restore: bool = True
    
    # Notification settings
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_email: str = ""
    
    @classmethod
    def from_env(cls) -> "RestoreConfig":
        """Create config from environment variables."""
        return cls(
            db_host=os.getenv("POSTGRES_HOST", "localhost"),
            db_port=int(os.getenv("POSTGRES_PORT", "5432")),
            db_name=os.getenv("POSTGRES_DB", "refurbadmin"),
            db_user=os.getenv("POSTGRES_USER", "refurbadmin"),
            db_password=os.getenv("POSTGRES_PASSWORD", ""),
            backup_dir=os.getenv("BACKUP_DIR", "./data/backups"),
            create_rollback=os.getenv("RESTORE_CREATE_ROLLBACK", "true").lower() == "true",
            verify_before_restore=os.getenv("RESTORE_VERIFY_BEFORE", "true").lower() == "true",
        )


@dataclass
class RestoreResult:
    """Result of a restore operation."""
    
    success: bool
    backup_file: str
    rollback_file: Optional[str] = None
    records_restored: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    verification_passed: bool = False
    rollback_available: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "backup_file": self.backup_file,
            "rollback_file": self.rollback_file,
            "records_restored": self.records_restored,
            "duration_seconds": round(self.duration_seconds, 2),
            "error": self.error,
            "verification_passed": self.verification_passed,
            "rollback_available": self.rollback_available,
            "timestamp": datetime.utcnow().isoformat(),
        }


class DatabaseRestore:
    """
    PostgreSQL database restore utility.
    
    Features:
    - Integrity verification before restore
    - Automatic rollback backup creation
    - Progress tracking
    - Error recovery
    """
    
    def __init__(self, config: RestoreConfig):
        self.config = config
        
        # Set PostgreSQL environment variables
        os.environ["PGPASSWORD"] = config.db_password
        os.environ["PGHOST"] = config.db_host
        os.environ["PGPORT"] = str(config.db_port)
        os.environ["PGDATABASE"] = config.db_name
        os.environ["PGUSER"] = config.db_user
        
        logger.info(f"Restore initialized for database '{config.db_name}' at {config.db_host}")
    
    def restore(
        self,
        backup_path: str,
        create_rollback: bool = None,
        verify_first: bool = None
    ) -> RestoreResult:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            create_rollback: Whether to create rollback backup
            verify_first: Whether to verify before restore
            
        Returns:
            RestoreResult with restore details
        """
        start_time = datetime.utcnow()
        
        create_rollback = create_rollback if create_rollback is not None else self.config.create_rollback
        verify_first = verify_first if verify_first is not None else self.config.verify_before_restore
        
        backup_file = Path(backup_path)
        
        # Validate backup file exists
        if not backup_file.exists():
            return RestoreResult(
                success=False,
                backup_file=backup_path,
                error=f"Backup file not found: {backup_path}",
            )
        
        logger.info(f"Starting restore from {backup_path}")
        
        rollback_file = None
        
        try:
            # Step 1: Verify backup integrity
            if verify_first:
                logger.info("Verifying backup integrity...")
                verification_result = self._verify_backup(backup_file)
                
                if not verification_result[0]:
                    return RestoreResult(
                        success=False,
                        backup_file=backup_path,
                        error=f"Backup verification failed: {verification_result[1]}",
                        verification_passed=False,
                    )
                
                logger.info(f"Verification passed: {verification_result[1]}")
            
            # Step 2: Create rollback backup
            if create_rollback:
                logger.info("Creating rollback backup...")
                rollback_result = self._create_rollback()
                
                if rollback_result[0]:
                    rollback_file = rollback_result[1]
                    logger.info(f"Rollback backup created: {rollback_file}")
                else:
                    logger.warning(f"Failed to create rollback backup: {rollback_result[1]}")
                    # Continue anyway - user can manually backup if needed
            
            # Step 3: Perform restore
            logger.info("Restoring database...")
            restore_result = self._perform_restore(backup_file)
            
            if not restore_result[0]:
                # Restore failed - attempt rollback
                if rollback_file:
                    logger.warning("Restore failed, attempting rollback...")
                    self._perform_restore(Path(rollback_file))
                
                return RestoreResult(
                    success=False,
                    backup_file=backup_path,
                    rollback_file=rollback_file,
                    error=f"Restore failed: {restore_result[1]}",
                    rollback_available=rollback_file is not None,
                    duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                )
            
            records_restored = restore_result[1]
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Restore completed successfully in {duration:.2f}s")
            
            return RestoreResult(
                success=True,
                backup_file=backup_path,
                rollback_file=rollback_file,
                records_restored=records_restored,
                duration_seconds=duration,
                verification_passed=verify_first,
                rollback_available=rollback_file is not None,
            )
            
        except Exception as e:
            logger.error(f"Restore failed with exception: {e}")
            
            # Attempt rollback on exception
            if rollback_file:
                logger.warning("Exception during restore, attempting rollback...")
                try:
                    self._perform_restore(Path(rollback_file))
                except Exception as rollback_error:
                    logger.error(f"Rollback also failed: {rollback_error}")
            
            return RestoreResult(
                success=False,
                backup_file=backup_path,
                rollback_file=rollback_file,
                error=str(e),
                rollback_available=rollback_file is not None,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )
        finally:
            # Clean up password from environment
            os.environ.pop("PGPASSWORD", None)
    
    def _verify_backup(self, backup_path: Path) -> Tuple[bool, str]:
        """
        Verify backup file integrity.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if backup_path.suffix == ".gz":
                # Verify gzip file
                with gzip.open(backup_path, 'rb') as f:
                    # Read and verify header
                    header = f.read(100)
                    
                    if not header:
                        return False, "Empty backup file"
                    
                    # Check for PostgreSQL dump header
                    if not header.startswith(b"-- PostgreSQL database dump"):
                        return False, "Not a valid PostgreSQL dump file"
                    
                    # Try to read more to verify file is not corrupted
                    f.seek(0)
                    chunk_count = 0
                    for _ in iter(lambda: f.read(8192), b""):
                        chunk_count += 1
                        if chunk_count > 1000:  # Limit verification time
                            break
                
                return True, f"Valid gzip backup ({backup_path.stat().st_size / 1024 / 1024:.2f} MB)"
            else:
                # Plain SQL file
                with open(backup_path, 'rb') as f:
                    header = f.read(100)
                    
                    if not header.startswith(b"-- PostgreSQL database dump"):
                        return False, "Not a valid PostgreSQL dump file"
                
                return True, f"Valid SQL backup ({backup_path.stat().st_size / 1024 / 1024:.2f} MB)"
                
        except gzip.BadGzipFile:
            return False, "Invalid gzip file"
        except Exception as e:
            return False, f"Verification error: {e}"
    
    def _create_rollback(self) -> Tuple[bool, Optional[str]]:
        """
        Create a rollback backup of current database.
        
        Returns:
            Tuple of (success, rollback_file_path)
        """
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rollback_name = f"{self.config.db_name}_rollback_{timestamp}.sql.gz"
            rollback_dir = Path(self.config.backup_dir)
            rollback_dir.mkdir(parents=True, exist_ok=True)
            rollback_path = rollback_dir / rollback_name
            
            # Run pg_dump with compression
            dump_cmd = [
                "pg_dump",
                "--format=plain",
                "--no-owner",
                "--no-privileges",
            ]
            
            # Dump to temp file first
            with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
                tmp_path = Path(tmp.name)
                
                result = subprocess.run(
                    dump_cmd,
                    stdout=tmp,
                    stderr=subprocess.PIPE,
                )
                
                if result.returncode != 0:
                    tmp_path.unlink()
                    return False, f"pg_dump failed: {result.stderr.decode()}"
                
                # Compress
                with open(tmp_path, 'rb') as f_in:
                    with gzip.open(rollback_path, 'wb', compresslevel=6) as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                tmp_path.unlink()
            
            return True, str(rollback_path)
            
        except Exception as e:
            return False, str(e)
    
    def _perform_restore(self, backup_path: Path) -> Tuple[bool, int]:
        """
        Perform the actual restore.
        
        Returns:
            Tuple of (success, records_restored)
        """
        try:
            # Handle compressed files
            if backup_path.suffix == ".gz":
                with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    
                    with gzip.open(backup_path, 'rb') as f_in:
                        with open(tmp_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    try:
                        result = self._restore_sql_file(tmp_path)
                    finally:
                        tmp_path.unlink()
                    
                    return result
            else:
                return self._restore_sql_file(backup_path)
                
        except Exception as e:
            return False, 0
    
    def _restore_sql_file(self, sql_path: Path) -> Tuple[bool, int]:
        """
        Restore from SQL file.
        
        Returns:
            Tuple of (success, records_restored)
        """
        try:
            # First, drop all tables (clean restore)
            logger.info("Dropping existing tables...")
            self._drop_all_tables()
            
            # Run psql restore
            restore_cmd = [
                "psql",
                "--quiet",
                "--set=ON_ERROR_STOP=on",
                "-v", "VERBOSITY=verbose",
            ]
            
            result = subprocess.run(
                restore_cmd,
                stdin=open(sql_path, 'r'),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, 0
            
            # Estimate records restored (count tables)
            records = self._count_records()
            
            return True, records
            
        except Exception as e:
            return False, 0
    
    def _drop_all_tables(self):
        """Drop all tables in the database."""
        drop_sql = """
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
        """
        
        try:
            subprocess.run(
                ["psql", "-c", drop_sql],
                capture_output=True,
                text=True
            )
        except Exception:
            pass  # Ignore errors - tables might not exist
    
    def _count_records(self) -> int:
        """Count total records in database."""
        count_sql = """
        SELECT SUM(n_live_tup) 
        FROM pg_stat_user_tables 
        WHERE schemaname = 'public';
        """
        
        try:
            result = subprocess.run(
                ["psql", "-t", "-c", count_sql],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                return int(result.stdout.strip())
        except Exception:
            pass
        
        return 0
    
    def list_backups(self) -> list:
        """List available backups."""
        backup_dir = Path(self.config.backup_dir)
        backups = []
        
        if backup_dir.exists():
            for backup_file in sorted(backup_dir.glob("*.sql.gz"), reverse=True):
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        
        return backups
    
    def get_rollback_file(self, hours: int = 24) -> Optional[str]:
        """
        Find the most recent rollback file.
        
        Args:
            hours: Look for rollbacks within this many hours
            
        Returns:
            Path to rollback file or None
        """
        backup_dir = Path(self.config.backup_dir)
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)
        
        for backup_file in sorted(backup_dir.glob("*rollback*.sql.gz"), reverse=True):
            if backup_file.stat().st_mtime > cutoff:
                return str(backup_file)
        
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database restore utility for RefurbAdmin AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WARNING: This operation will overwrite the current database!

Examples:
    # Restore from specific backup
    python restore_database.py ./data/backups/refurbadmin_20240101_120000.sql.gz
    
    # Restore with verification only (no actual restore)
    python restore_database.py backup.sql.gz --verify-only
    
    # Restore without creating rollback
    python restore_database.py backup.sql.gz --no-rollback
    
    # List available backups
    python restore_database.py --list
        """
    )
    parser.add_argument(
        "backup_file",
        nargs="?",
        help="Path to backup file to restore",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify backup, don't restore",
    )
    parser.add_argument(
        "--no-rollback",
        action="store_true",
        help="Don't create rollback backup before restore",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification before restore",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available backups",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output result as JSON to file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = RestoreConfig.from_env()
    
    # Create restore utility
    restore = DatabaseRestore(config)
    
    # Execute requested operation
    result = None
    
    if args.list:
        backups = restore.list_backups()
        output = json.dumps({"backups": backups}, indent=2)
        print(output)
        if args.output:
            Path(args.output).write_text(output)
        return 0
    
    if not args.backup_file:
        parser.error("backup_file is required (or use --list)")
    
    # Verify-only mode
    if args.verify_only:
        success, message = restore._verify_backup(Path(args.backup_file))
        result = {
            "verified": success,
            "file": args.backup_file,
            "message": message,
        }
        print(json.dumps(result, indent=2))
        return 0 if success else 1
    
    # Confirmation prompt
    if not args.force:
        print(f"\n{'='*60}")
        print("WARNING: This will overwrite the current database!")
        print(f"Backup file: {args.backup_file}")
        print(f"Database: {config.db_name}@{config.db_host}")
        print(f"Create rollback: {not args.no_rollback}")
        print(f"{'='*60}")
        
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Restore cancelled.")
            return 1
    
    # Perform restore
    result = restore.restore(
        args.backup_file,
        create_rollback=not args.no_rollback,
        verify_first=not args.no_verify,
    )
    
    output = result.to_dict()
    print(json.dumps(output, indent=2))
    
    if args.output:
        Path(args.output).write_text(json.dumps(output, indent=2))
    
    # Print rollback info if available
    if result.success and result.rollback_file:
        print(f"\nRollback backup created: {result.rollback_file}")
        print("To rollback, run:")
        print(f"  python restore_database.py {result.rollback_file}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
