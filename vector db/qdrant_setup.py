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
                print("✅ Qdrant is already running!")

        elif command == "stop":
            stop_qdrant()

        else:
            print("Usage: python qdrant_setup.py [start|stop]")
            print("\nCommands:")
            print("  start    - Start Qdrant container")
            print("  stop     - Stop Qdrant container")
    else:
        print("Use Start or Stop command")
