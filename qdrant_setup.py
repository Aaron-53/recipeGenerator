#!/usr/bin/env python3
"""
Helper script to start Qdrant locally using Docker.
Make sure Docker is installed and running before using this script.
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path

QDRANT_PORT = 6333
CONTAINER_NAME = "qdrant_local"
STORAGE_DIR = os.path.join(os.getcwd(), "qdrant_storage")  # Local storage directory
CONTAINER_STORAGE_PATH = "/qdrant/storage"  # Path inside container


def ensure_storage_directory():
    """Ensure the local storage directory exists"""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR)
        print(f"📁 Created storage directory: {STORAGE_DIR}")
    else:
        print(f"📁 Using storage directory: {STORAGE_DIR}")
    return STORAGE_DIR


def get_storage_info():
    """Get information about data storage location"""
    storage_path = Path(STORAGE_DIR).resolve()
    size_mb = 0
    file_count = 0

    if os.path.exists(STORAGE_DIR):
        for root, dirs, files in os.walk(STORAGE_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    size_mb += os.path.getsize(filepath)
                    file_count += 1
                except:
                    pass
        size_mb = size_mb / (1024 * 1024)  # Convert to MB

    return {
        "path": str(storage_path),
        "size_mb": size_mb,
        "file_count": file_count,
        "exists": os.path.exists(STORAGE_DIR),
    }


def show_storage_info():
    """Display storage information"""
    info = get_storage_info()
    print(f"\n💾 Qdrant Data Storage:")
    print(f"   Location: {info['path']}")

    if info["exists"]:
        print(f"   Size: {info['size_mb']:.2f} MB")
        print(f"   Files: {info['file_count']}")
        print(f"   Status: ✅ Data directory exists")
    else:
        print(f"   Status: ❌ No data directory found")


def backup_data(backup_path=None):
    """Create a backup of Qdrant data"""
    import shutil

    if not os.path.exists(STORAGE_DIR):
        print("❌ No data directory found to backup")
        return False

    if backup_path is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"qdrant_backup_{timestamp}"

    try:
        print(f"📦 Creating backup at: {backup_path}")
        shutil.copytree(STORAGE_DIR, backup_path)

        # Get backup size
        backup_info = get_storage_info()
        print(f"✅ Backup completed: {backup_info['size_mb']:.2f} MB")
        print(f"📁 Backup location: {os.path.abspath(backup_path)}")
        return True

    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def restore_data(backup_path):
    """Restore Qdrant data from backup"""
    import shutil

    if not os.path.exists(backup_path):
        print(f"❌ Backup directory not found: {backup_path}")
        return False

    # Stop Qdrant if running
    if check_qdrant_running():
        print("🛑 Stopping Qdrant for restoration...")
        stop_qdrant()
        time.sleep(2)

    try:
        # Remove existing data
        if os.path.exists(STORAGE_DIR):
            print(f"🗑️ Removing existing data directory...")
            shutil.rmtree(STORAGE_DIR)

        # Restore from backup
        print(f"📦 Restoring data from: {backup_path}")
        shutil.copytree(backup_path, STORAGE_DIR)

        print("✅ Data restoration completed")
        print("🔄 You can now start Qdrant to use the restored data")
        return True

    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        return False


def check_docker():
    """Check if Docker is available"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass

    print("❌ Docker not found. Please install Docker first.")
    print("Download from: https://www.docker.com/get-started")
    return False


def check_qdrant_running():
    """Check if Qdrant is already running"""
    print("Checking if Qdrant is running...")
    try:
        print(f"Trying to connect to Qdrant at http://localhost:{QDRANT_PORT}/")
        response = requests.get(f"http://localhost:{QDRANT_PORT}/", timeout=5)
        print(f"Received response from Qdrant: {response.status_code}")
        if response.status_code == 200:
            print("✅ Qdrant is already running!")
            return True
    except (requests.exceptions.ReadTimeout, requests.exceptions.Timeout):
        print("⏱️ Connection timeout - Qdrant is not responding")
    except requests.exceptions.ConnectionError:
        print("ℹ️ Qdrant is not running.")
    except Exception as e:
        print(f"❌ Error checking Qdrant status: {e}")
    return False


def start_qdrant():
    """Start Qdrant container with persistent storage"""
    print("Starting Qdrant container...")

    # Ensure storage directory exists
    storage_path = ensure_storage_directory()

    # Stop existing container if running
    subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True)
    subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)

    # Start new container with volume mount
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        CONTAINER_NAME,
        "-p",
        f"{QDRANT_PORT}:{QDRANT_PORT}",
        "-p",
        "6334:6334",
        "-v",
        f"{storage_path}:{CONTAINER_STORAGE_PATH}",  # Mount persistent storage
        "qdrant/qdrant:latest",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("🐳 Qdrant container started!")

            # Wait for Qdrant to be ready
            print("⏳ Waiting for Qdrant to be ready...")
            for i in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                if check_qdrant_running():
                    print("✅ Qdrant is ready!")
                    print(
                        f"🌐 Access Qdrant dashboard at: http://localhost:{QDRANT_PORT}/dashboard"
                    )
                    print(f"💾 Data stored in: {storage_path}")
                    return True
                print(f"   Checking... {i + 1}/30")

            print("❌ Qdrant didn't start within 30 seconds")
            return False

        else:
            print(f"❌ Failed to start container: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error starting Qdrant: {e}")
        return False


def stop_qdrant():
    """Stop Qdrant container"""
    print("Stopping Qdrant container...")
    try:
        result = subprocess.run(
            ["docker", "stop", CONTAINER_NAME], capture_output=True, text=True
        )
        if result.returncode == 0:
            print("🛑 Qdrant container stopped")
            subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)
            print("🗑️ Container removed")
        else:
            print("ℹ️ Container might not be running")
    except Exception as e:
        print(f"❌ Error stopping Qdrant: {e}")


def show_status():
    """Show current Qdrant status"""
    if check_qdrant_running():
        print("📊 Qdrant Status: RUNNING")
        print(f"🌐 Dashboard: http://localhost:{QDRANT_PORT}/dashboard")
        print(f"🔌 API: http://localhost:{QDRANT_PORT}")

        # Show storage info
        show_storage_info()

        # Show container info
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={CONTAINER_NAME}",
                    "--format",
                    "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and len(result.stdout.strip().split("\n")) > 1:
                print("\n📦 Container Info:")
                print(result.stdout)
        except:
            pass
    else:
        print("📊 Qdrant Status: NOT RUNNING")
        show_storage_info()


if __name__ == "__main__":
    print("Qdrant Local Setup Helper")
    print("=" * 30)

    if not check_docker():
        sys.exit(1)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "start":
            if not check_qdrant_running():
                start_qdrant()
            else:
                show_status()

        elif command == "stop":
            stop_qdrant()

        elif command == "status":
            show_status()

        elif command == "restart":
            stop_qdrant()
            time.sleep(2)
            start_qdrant()

        elif command == "backup":
            backup_path = sys.argv[2] if len(sys.argv) > 2 else None
            backup_data(backup_path)

        elif command == "restore":
            if len(sys.argv) > 2:
                restore_data(sys.argv[2])
            else:
                print("Usage: python qdrant_setup.py restore <backup_path>")

        elif command == "storage":
            show_storage_info()

        else:
            print(
                "Usage: python qdrant_setup.py [start|stop|status|restart|backup|restore|storage]"
            )
            print("\nData Management:")
            print("  backup [path]     - Create backup of Qdrant data")
            print("  restore <path>    - Restore data from backup")
            print("  storage           - Show storage information")
    else:
        # Interactive mode
        print("\nSelect an action:")
        print("1. Start Qdrant")
        print("2. Stop Qdrant")
        print("3. Show Status")
        print("4. Restart Qdrant")
        print("5. Backup Data")
        print("6. Show Storage Info")

        choice = input("\nEnter choice (1-6): ").strip()

        if choice == "1":
            if not check_qdrant_running():
                print("Starting Qdrant...")
                start_qdrant()
            else:
                print("Qdrant is already running. Showing status...")
                show_status()
        elif choice == "2":
            stop_qdrant()
        elif choice == "3":
            show_status()
        elif choice == "4":
            stop_qdrant()
            time.sleep(2)
            start_qdrant()
        elif choice == "5":
            backup_data()
        elif choice == "6":
            show_storage_info()
        else:
            print("Invalid choice")
