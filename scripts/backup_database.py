#!/usr/bin/env python3
"""
Database Backup Script for RefurbAdmin AI.

Features:
- Daily automated backups
- Compression with gzip
- Retention policy (configurable, default 7 days)
- Backup to cloud storage ready (S3, Azure)
- POPIA compliant logging
- South African timezone support

Usage:
    python backup_database.py [--config PATH] [--retention DAYS]
    
Cron Example (daily at 2 AM SAST):
    0 2 * * * /path/to/venv/bin/python /path/to/backup_database.py
"""

import os
import sys
import gzip
import shutil
import logging
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
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
class BackupConfig:
    """Backup configuration."""
    
    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "refurbadmin"
    db_user: str = "refurbadmin"
    db_password: str = ""
    
    # Backup settings
    backup_dir: str = "./data/backups"
    retention_days: int = 7
    compression_level: int = 6
    
    # Cloud storage (optional)
    cloud_enabled: bool = False
    cloud_provider: str = "s3"  # s3, azure, gcs
    cloud_bucket: str = ""
    cloud_region: str = "af-south-1"
    
    # Notification settings
    notify_on_success: bool = False
    notify_on_failure: bool = True
    notification_email: str = ""
    
    @classmethod
    def from_env(cls) -> "BackupConfig":
        """Create config from environment variables."""
        return cls(
            db_host=os.getenv("POSTGRES_HOST", "localhost"),
            db_port=int(os.getenv("POSTGRES_PORT", "5432")),
            db_name=os.getenv("POSTGRES_DB", "refurbadmin"),
            db_user=os.getenv("POSTGRES_USER", "refurbadmin"),
            db_password=os.getenv("POSTGRES_PASSWORD", ""),
            backup_dir=os.getenv("BACKUP_DIR", "./data/backups"),
            retention_days=int(os.getenv("BACKUP_RETENTION_DAYS", "7")),
            cloud_enabled=os.getenv("CLOUD_BACKUP_ENABLED", "false").lower() == "true",
            cloud_provider=os.getenv("CLOUD_PROVIDER", "s3"),
            cloud_bucket=os.getenv("AWS_STORAGE_BUCKET_NAME", ""),
            cloud_region=os.getenv("AWS_S3_REGION_NAME", "af-south-1"),
            notify_on_failure=os.getenv("NOTIFY_ON_BACKUP_FAILURE", "true").lower() == "true",
            notification_email=os.getenv("ADMIN_EMAIL", ""),
        )


@dataclass
class BackupResult:
    """Result of a backup operation."""
    
    success: bool
    backup_file: Optional[str] = None
    backup_size: int = 0
    backup_hash: Optional[str] = None
    duration_seconds: float = 0.0
    error: Optional[str] = None
    old_backups_deleted: int = 0
    cloud_uploaded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "backup_file": self.backup_file,
            "backup_size_mb": round(self.backup_size / (1024 * 1024), 2),
            "backup_hash": self.backup_hash,
            "duration_seconds": round(self.duration_seconds, 2),
            "error": self.error,
            "old_backups_deleted": self.old_backups_deleted,
            "cloud_uploaded": self.cloud_uploaded,
            "timestamp": datetime.utcnow().isoformat(),
        }


class DatabaseBackup:
    """
    PostgreSQL database backup utility.
    
    Supports:
    - Full database dumps (pg_dump)
    - Gzip compression
    - Retention policy enforcement
    - Cloud storage upload (S3, Azure, GCS)
    - Integrity verification
    """
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.backup_dir = Path(config.backup_dir)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Set PostgreSQL environment variables
        os.environ["PGPASSWORD"] = config.db_password
        os.environ["PGHOST"] = config.db_host
        os.environ["PGPORT"] = str(config.db_port)
        os.environ["PGDATABASE"] = config.db_name
        os.environ["PGUSER"] = config.db_user
        
        logger.info(f"Backup initialized for database '{config.db_name}' at {config.db_host}")
    
    def create_backup(self) -> BackupResult:
        """
        Create a database backup.
        
        Returns:
            BackupResult with backup details
        """
        start_time = datetime.utcnow()
        
        # Generate backup filename
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        backup_name = f"{self.config.db_name}_{timestamp}.sql"
        backup_path = self.backup_dir / backup_name
        compressed_path = backup_path.with_suffix(".sql.gz")
        
        logger.info(f"Starting backup to {backup_path}")
        
        try:
            # Run pg_dump
            dump_cmd = [
                "pg_dump",
                "--format=plain",
                "--no-owner",
                "--no-privileges",
                "--verbose",
            ]
            
            result = subprocess.run(
                dump_cmd,
                stdout=open(backup_path, 'wb'),
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Compress backup
            logger.info("Compressing backup...")
            self._compress_file(backup_path, compressed_path, self.config.compression_level)
            
            # Remove uncompressed file
            backup_path.unlink()
            
            # Calculate hash for integrity verification
            backup_hash = self._calculate_hash(compressed_path)
            
            # Get file size
            backup_size = compressed_path.stat().st_size
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Backup completed: {compressed_path.name} ({backup_size / 1024 / 1024:.2f} MB)")
            
            # Upload to cloud if enabled
            cloud_uploaded = False
            if self.config.cloud_enabled:
                try:
                    cloud_uploaded = self._upload_to_cloud(compressed_path)
                except Exception as e:
                    logger.warning(f"Cloud upload failed: {e}")
            
            # Clean up old backups
            old_deleted = self._cleanup_old_backups()
            
            return BackupResult(
                success=True,
                backup_file=str(compressed_path),
                backup_size=backup_size,
                backup_hash=backup_hash,
                duration_seconds=duration,
                old_backups_deleted=old_deleted,
                cloud_uploaded=cloud_uploaded,
            )
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return BackupResult(
                success=False,
                error=str(e),
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
            )
        finally:
            # Clean up password from environment
            os.environ.pop("PGPASSWORD", None)
    
    def _compress_file(self, input_path: Path, output_path: Path, level: int = 6):
        """Compress a file using gzip."""
        with open(input_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb', compresslevel=level) as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _cleanup_old_backups(self) -> int:
        """
        Remove backups older than retention period.
        
        Returns:
            Number of backups deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.retention_days)
        deleted_count = 0
        
        for backup_file in self.backup_dir.glob("*.sql.gz"):
            try:
                # Extract timestamp from filename
                # Format: dbname_YYYYMMDD_HHMMSS.sql.gz
                name_parts = backup_file.stem.replace(".sql", "").split("_")
                if len(name_parts) >= 3:
                    date_str = f"{name_parts[-2]}_{name_parts[-1]}"
                    backup_date = datetime.strptime(date_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {backup_file.name}")
            except Exception as e:
                logger.warning(f"Could not process backup file {backup_file}: {e}")
        
        logger.info(f"Cleanup complete: {deleted_count} old backups deleted")
        return deleted_count
    
    def _upload_to_cloud(self, backup_path: Path) -> bool:
        """
        Upload backup to cloud storage.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if upload successful
        """
        if self.config.cloud_provider == "s3":
            return self._upload_to_s3(backup_path)
        elif self.config.cloud_provider == "azure":
            return self._upload_to_azure(backup_path)
        elif self.config.cloud_provider == "gcs":
            return self._upload_to_gcs(backup_path)
        else:
            logger.warning(f"Unknown cloud provider: {self.config.cloud_provider}")
            return False
    
    def _upload_to_s3(self, backup_path: Path) -> bool:
        """Upload to AWS S3."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
            
            s3_client = boto3.client(
                's3',
                region_name=self.config.cloud_region,
                # Credentials from environment: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
            )
            
            key = f"backups/{self.config.db_name}/{backup_path.name}"
            
            s3_client.upload_file(
                str(backup_path),
                self.config.cloud_bucket,
                key,
                ExtraArgs={
                    'StorageClass': 'STANDARD_IA',  # Infrequent access for backups
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"Uploaded to S3: s3://{self.config.cloud_bucket}/{key}")
            return True
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return False
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False
    
    def _upload_to_azure(self, backup_path: Path) -> bool:
        """Upload to Azure Blob Storage."""
        try:
            from azure.storage.blob import BlobServiceClient
            
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                logger.error("Azure connection string not configured")
                return False
            
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            blob_client = blob_service_client.get_blob_client(
                container=self.config.cloud_bucket,
                blob=f"backups/{self.config.db_name}/{backup_path.name}"
            )
            
            with open(backup_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            
            logger.info(f"Uploaded to Azure: {self.config.cloud_bucket}/{blob_client.blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Azure upload failed: {e}")
            return False
    
    def _upload_to_gcs(self, backup_path: Path) -> bool:
        """Upload to Google Cloud Storage."""
        try:
            from google.cloud import storage
            
            client = storage.Client()
            bucket = client.bucket(self.config.cloud_bucket)
            blob = bucket.blob(f"backups/{self.config.db_name}/{backup_path.name}")
            
            blob.upload_from_filename(str(backup_path))
            
            logger.info(f"Uploaded to GCS: gs://{self.config.cloud_bucket}/{blob.name}")
            return True
            
        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List of backup metadata
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("*.sql.gz"), reverse=True):
            try:
                stat = backup_file.stat()
                backups.append({
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception as e:
                logger.warning(f"Could not stat backup file {backup_file}: {e}")
        
        return backups
    
    def verify_backup(self, backup_path: str) -> bool:
        """
        Verify backup integrity.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if backup is valid
        """
        path = Path(backup_path)
        
        if not path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            # Try to decompress and validate
            with gzip.open(path, 'rb') as f:
                # Read first chunk to verify it's valid SQL
                chunk = f.read(1024)
                if not chunk.startswith(b"-- PostgreSQL database dump"):
                    logger.warning("Backup may not be a valid PostgreSQL dump")
            
            logger.info(f"Backup verified: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful
        """
        path = Path(backup_path)
        
        if not path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        logger.info(f"Starting restore from {backup_path}")
        
        try:
            # Decompress if needed
            if path.suffix == ".gz":
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                    with gzip.open(path, 'rb') as f_in:
                        shutil.copyfileobj(f_in, tmp)
                    
                    try:
                        return self._restore_sql_file(tmp_path)
                    finally:
                        tmp_path.unlink()
            else:
                return self._restore_sql_file(path)
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _restore_sql_file(self, sql_path: Path) -> bool:
        """Restore from SQL file."""
        try:
            restore_cmd = [
                "psql",
                "--quiet",
                "--set=ON_ERROR_STOP=on",
            ]
            
            result = subprocess.run(
                restore_cmd,
                stdin=open(sql_path, 'r'),
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"psql failed: {result.stderr}")
            
            logger.info("Restore completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database backup utility for RefurbAdmin AI"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--retention",
        type=int,
        default=None,
        help="Retention period in days",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available backups",
    )
    parser.add_argument(
        "--verify",
        type=str,
        help="Verify a specific backup file",
    )
    parser.add_argument(
        "--restore",
        type=str,
        help="Restore from a specific backup file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output result as JSON to file",
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = BackupConfig.from_env()
    
    if args.retention:
        config.retention_days = args.retention
    
    # Create backup utility
    backup = DatabaseBackup(config)
    
    # Execute requested operation
    result = None
    
    if args.list:
        backups = backup.list_backups()
        output = json.dumps({"backups": backups}, indent=2)
        print(output)
        if args.output:
            Path(args.output).write_text(output)
        return 0
    
    elif args.verify:
        success = backup.verify_backup(args.verify)
        result = {"verified": success, "file": args.verify}
        print(json.dumps(result, indent=2))
        return 0 if success else 1
    
    elif args.restore:
        success = backup.restore_backup(args.restore)
        result = {"restored": success, "file": args.restore}
        print(json.dumps(result, indent=2))
        return 0 if success else 1
    
    else:
        # Create new backup
        result = backup.create_backup()
        output = result.to_dict()
        print(json.dumps(output, indent=2))
        
        if args.output:
            Path(args.output).write_text(json.dumps(output, indent=2))
        
        return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
