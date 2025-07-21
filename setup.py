#!/usr/bin/env python3
"""
Judge0 Setup Script
Automated setup for the Judge0 Docker CLI system
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status"""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False


def check_requirements():
    """Check if required tools are installed"""
    print("🔍 Checking requirements...")
    
    requirements = [
        ("python", "python --version"),
        ("docker", "docker --version"),
        ("pip", "pip --version")
    ]
    
    all_good = True
    for name, command in requirements:
        if run_command(command, f"Checking {name}"):
            continue
        else:
            print(f"❌ {name} is not installed or not in PATH")
            all_good = False
    
    return all_good


def setup_environment():
    """Setup the development environment"""
    print("\n🚀 Setting up Judge0 Docker CLI environment...")
    
    # Create .env file if it doesn't exist
    if not os.path.exists(".env"):
        if run_command("copy .env.example .env" if os.name == 'nt' else "cp .env.example .env", "Creating .env file"):
            print("📝 Please review and update the .env file with your configuration")
        else:
            print("❌ Failed to create .env file")
            return False
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Check Docker connection
    if not run_command("docker ps", "Testing Docker connection"):
        print("❌ Docker is not running or not accessible")
        return False
    
    print("\n✅ Environment setup completed successfully!")
    print("\nNext steps:")
    print("1. Review and update .env file with your settings")
    print("2. Start PostgreSQL database (if using PostgreSQL)")
    print("3. Initialize database: python scripts/init_db.py")
    print("4. Start the API server: python -m api.main")
    print("5. Run multi-worker stress test: python multi_worker_stress_test.py")
    
    return True


def main():
    """Main setup function"""
    print("🎯 Judge0 Docker CLI Setup")
    print("=" * 50)
    
    if not check_requirements():
        print("\n❌ Please install missing requirements and try again")
        sys.exit(1)
    
    if not setup_environment():
        print("\n❌ Setup failed. Please check the errors above")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("Run 'python -m api.main' to start the server")


if __name__ == "__main__":
    main()
