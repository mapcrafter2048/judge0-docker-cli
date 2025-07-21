"""Setup script for Judge0 Docker CLI project."""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, check=True):
    """Run a shell command."""
    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=True, text=True
        )
        if result.stdout:
            print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{command}': {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def setup_environment():
    """Set up the development environment."""
    print("Setting up Judge0 Docker CLI development environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required.")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Check if Docker is available
    if not run_command("docker --version", check=False):
        print("❌ Docker is not installed or not available in PATH")
        print("Please install Docker from https://docs.docker.com/get-docker/")
        sys.exit(1)
    
    print("✅ Docker is available")
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt"):
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    print("✅ Python dependencies installed")
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("Creating .env file from .env.example...")
        env_content = env_example.read_text()
        env_file.write_text(env_content)
        print("✅ .env file created")
        print("📝 Please edit .env file with your configuration")
    
    # Test Docker connectivity
    print("Testing Docker connectivity...")
    if not run_command("docker info", check=False):
        print("⚠️  Docker daemon might not be running")
        print("Please start Docker and try again")
    else:
        print("✅ Docker daemon is running")
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your configuration")
    print("2. Initialize database: python scripts/init_db.py")
    print("3. Start the API: python -m api.main")
    print("4. Run tests: python fast_queue_test.py")


if __name__ == "__main__":
    setup_environment()