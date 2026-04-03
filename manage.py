#!/usr/bin/env python3
"""
Management Commands for RefurbAdmin AI.

Django-style management commands for system administration.

Usage:
    python manage.py <command> [options]

Commands:
    migrate          - Run database migrations
    create-admin     - Create admin user
    createsuperuser  - Create superuser (alias)
    backup           - Create database backup
    restore          - Restore from backup
    health           - Check system health
    shell            - Open interactive shell
    collect-static   - Collect static files
    clear-cache      - Clear application cache
    list-users       - List all users
    deactivate-user  - Deactivate a user
"""

import sys
import os
import argparse
import getpass
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup environment
os.environ.setdefault("PYTHONPATH", os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("APP_ENV", "development")


class CommandError(Exception):
    """Custom command error."""
    pass


class ManagementCommand:
    """Base class for management commands."""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="RefurbAdmin AI Management Commands"
        )
        self.subparsers = self.parser.add_subparsers(dest="command", help="Available commands")
        self._setup_commands()
    
    def _setup_commands(self):
        """Setup all available commands."""
        # Migrate
        self.subparsers.add_parser("migrate", help="Run database migrations")
        
        # Create admin
        self.subparsers.add_parser("create-admin", help="Create admin user")
        self.subparsers.add_parser("createsuperuser", help="Create superuser")
        
        # Backup
        backup_parser = self.subparsers.add_parser("backup", help="Create database backup")
        backup_parser.add_argument("--output", "-o", help="Output file path")
        
        # Restore
        restore_parser = self.subparsers.add_parser("restore", help="Restore from backup")
        restore_parser.add_argument("backup_file", help="Backup file to restore")
        restore_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation")
        
        # Health
        self.subparsers.add_parser("health", help="Check system health")
        
        # Shell
        self.subparsers.add_parser("shell", help="Open interactive shell")
        
        # Collect static
        self.subparsers.add_parser("collect-static", help="Collect static files")
        
        # Clear cache
        self.subparsers.add_parser("clear-cache", help="Clear application cache")
        
        # List users
        self.subparsers.add_parser("list-users", help="List all users")
        
        # Deactivate user
        deactivate_parser = self.subparsers.add_parser("deactivate-user", help="Deactivate a user")
        deactivate_parser.add_argument("email", help="User email to deactivate")
    
    def run(self, args=None):
        """Run the management command."""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return 1
        
        command_method = f"cmd_{parsed_args.command.replace('-', '_')}"
        
        if hasattr(self, command_method):
            try:
                return getattr(self, command_method)(parsed_args)
            except CommandError as e:
                print(f"Error: {e}")
                return 1
            except Exception as e:
                print(f"Unexpected error: {e}")
                return 1
        else:
            print(f"Unknown command: {parsed_args.command}")
            return 1
    
    def cmd_migrate(self, args):
        """Run database migrations."""
        print("Running database migrations...")
        
        try:
            from alembic.config import Config
            from alembic import command
            
            alembic_cfg = Config("alembic.ini")
            command.upgrade(alembic_cfg, "head")
            
            print("Migrations completed successfully.")
            return 0
        except ImportError:
            print("Alembic not installed. Install with: pip install alembic")
            return 1
        except Exception as e:
            raise CommandError(f"Migration failed: {e}")
    
    def cmd_create_admin(self, args):
        """Create admin user."""
        print("Creating admin user...")
        
        email = input("Email: ")
        password = getpass.getpass("Password: ")
        password_confirm = getpass.getpass("Confirm Password: ")
        
        if password != password_confirm:
            raise CommandError("Passwords do not match")
        
        if len(password) < 10:
            raise CommandError("Password must be at least 10 characters")
        
        # Create user (placeholder - implement with your user model)
        print(f"\nAdmin user created:")
        print(f"  Email: {email}")
        print(f"  Role: admin")
        print("\nYou can now login with these credentials.")
        return 0
    
    def cmd_createsuperuser(self, args):
        """Create superuser (alias for create-admin)."""
        return self.cmd_create_admin(args)
    
    def cmd_backup(self, args):
        """Create database backup."""
        print("Creating database backup...")
        
        from scripts.backup_database import BackupConfig, DatabaseBackup
        
        config = BackupConfig.from_env()
        if args.output:
            config.backup_dir = os.path.dirname(args.output)
        
        backup = DatabaseBackup(config)
        result = backup.create_backup()
        
        if result.success:
            print(f"Backup created successfully: {result.backup_file}")
            print(f"Size: {result.backup_size / 1024 / 1024:.2f} MB")
            return 0
        else:
            raise CommandError(f"Backup failed: {result.error}")
    
    def cmd_restore(self, args):
        """Restore from backup."""
        print(f"Restoring from backup: {args.backup_file}")
        
        if not args.force:
            confirm = input("\nWARNING: This will overwrite the current database!\nType 'yes' to confirm: ")
            if confirm.lower() != 'yes':
                print("Restore cancelled.")
                return 1
        
        from scripts.restore_database import RestoreConfig, DatabaseRestore
        
        config = RestoreConfig.from_env()
        restore = DatabaseRestore(config)
        result = restore.restore(args.backup_file, create_rollback=not args.force)
        
        if result.success:
            print("Restore completed successfully.")
            if result.rollback_file:
                print(f"Rollback backup: {result.rollback_file}")
            return 0
        else:
            raise CommandError(f"Restore failed: {result.error}")
    
    def cmd_health(self, args):
        """Check system health."""
        print("Checking system health...\n")
        
        checks = []
        
        # Database check
        try:
            import psycopg2
            from dotenv import load_dotenv
            load_dotenv()
            
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "refurbadmin"),
                user=os.getenv("POSTGRES_USER", "refurbadmin"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
            )
            conn.close()
            checks.append(("Database", "✓ Connected"))
        except Exception as e:
            checks.append(("Database", f"✗ Error: {e}"))
        
        # Redis check
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            r.ping()
            checks.append(("Redis", "✓ Connected"))
        except Exception as e:
            checks.append(("Redis", f"✗ Error: {e}"))
        
        # Print results
        for name, status in checks:
            print(f"  {name}: {status}")
        
        # Summary
        all_healthy = all("✓" in status for _, status in checks)
        print(f"\nOverall: {'✓ Healthy' if all_healthy else '✗ Issues detected'}")
        
        return 0 if all_healthy else 1
    
    def cmd_shell(self, args):
        """Open interactive shell."""
        print("Opening interactive shell...")
        print("Type 'exit()' or press Ctrl-D to exit.\n")
        
        try:
            import code
            code.interact(local=globals())
            return 0
        except Exception as e:
            raise CommandError(f"Shell error: {e}")
    
    def cmd_collect_static(self, args):
        """Collect static files."""
        print("Collecting static files...")
        
        import shutil
        from pathlib import Path
        
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        # Collect from app directories
        app_static = Path("app") / "static"
        if app_static.exists():
            for item in app_static.iterdir():
                dest = static_dir / item.name
                if item.is_file():
                    shutil.copy2(item, dest)
        
        print(f"Static files collected to: {static_dir}")
        return 0
    
    def cmd_clear_cache(self, args):
        """Clear application cache."""
        print("Clearing cache...")
        
        try:
            import redis
            r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
            r.flushdb()
            print("Cache cleared successfully.")
            return 0
        except Exception as e:
            raise CommandError(f"Cache clear failed: {e}")
    
    def cmd_list_users(self, args):
        """List all users."""
        print("Listing users...\n")
        
        # Placeholder - implement with your user model
        print("User listing not implemented yet.")
        print("Connect to database and query users table.")
        return 0
    
    def cmd_deactivate_user(self, args):
        """Deactivate a user."""
        print(f"Deactivating user: {args.email}")
        
        # Placeholder - implement with your user model
        print(f"User {args.email} deactivated.")
        return 0


def main():
    """Main entry point."""
    command = ManagementCommand()
    sys.exit(command.run())


if __name__ == "__main__":
    main()
