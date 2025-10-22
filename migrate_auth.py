"""
Quick setup script to apply new authentication system
Run this to automatically update your files
"""
import os
import shutil
from pathlib import Path

def backup_file(filepath):
    """Create backup of a file"""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backed up: {filepath} -> {backup_path}")
        return True
    return False

def rename_file(old_path, new_path):
    """Rename a file, backing up if target exists"""
    if os.path.exists(new_path):
        backup_file(new_path)
    
    if os.path.exists(old_path):
        shutil.move(old_path, new_path)
        print(f"✅ Renamed: {old_path} -> {new_path}")
        return True
    else:
        print(f"⚠️  File not found: {old_path}")
        return False

def main():
    print("=" * 60)
    print("🔧 Authentication System Migration Script")
    print("=" * 60)
    print()
    
    # Get project root
    script_dir = Path(__file__).parent
    backend_dir = script_dir / "backend"
    frontend_dir = script_dir / "frontend" / "src" / "components"
    
    print(f"Project root: {script_dir}")
    print(f"Backend dir: {backend_dir}")
    print(f"Frontend dir: {frontend_dir}")
    print()
    
    # Step 1: Backend files
    print("📦 Step 1: Updating backend files...")
    print("-" * 60)
    
    # Backup old files
    old_backend_files = [
        backend_dir / "auth.py",
        backend_dir / "google_auth.py"
    ]
    
    for file in old_backend_files:
        if file.exists():
            backup_file(str(file))
    
    # Rename new files
    rename_file(
        str(backend_dir / "auth_new.py"),
        str(backend_dir / "auth.py")
    )
    
    # auth_routes.py stays as is
    print("✅ auth_routes.py is ready to use")
    print()
    
    # Step 2: Frontend files
    print("📦 Step 2: Updating frontend files...")
    print("-" * 60)
    
    # Backup old files
    old_frontend_files = [
        frontend_dir / "AuthProvider.js",
        frontend_dir / "GoogleCallback.js",
        frontend_dir / "LoginButton.js"
    ]
    
    for file in old_frontend_files:
        if file.exists():
            backup_file(str(file))
    
    # Rename new files
    rename_file(
        str(frontend_dir / "AuthProvider_new.js"),
        str(frontend_dir / "AuthProvider.js")
    )
    
    rename_file(
        str(frontend_dir / "GoogleCallback_new.js"),
        str(frontend_dir / "GoogleCallback.js")
    )
    
    rename_file(
        str(frontend_dir / "LoginButton_new.js"),
        str(frontend_dir / "LoginButton.js")
    )
    
    print()
    print("=" * 60)
    print("✅ Migration complete!")
    print("=" * 60)
    print()
    print("📝 Next steps:")
    print("   1. Review AUTH_MIGRATION_GUIDE.md for details")
    print("   2. Update server.py imports (see guide)")
    print("   3. Verify .env file has required variables")
    print("   4. Test the authentication flow")
    print()
    print("🔄 To revert changes, restore from .backup files")
    print()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Please review the error and try again")
