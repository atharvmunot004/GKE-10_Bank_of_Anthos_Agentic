#!/usr/bin/env python3
"""
Docker-based integration test for consistency-manager-svc
"""

import subprocess
import time
import os
import json
import requests
from datetime import datetime

def run_command(command, cwd=None, check_error=True):
    """Runs a shell command and returns its output."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=check_error,
            capture_output=True,
            text=True
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def print_test_result(passed, test_name, details=""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"    Details: {details}")

def test_docker_build():
    """Test Docker image build."""
    print("\n1. Testing Docker image build...")
    try:
        stdout, stderr = run_command("docker build -t consistency-manager-svc-test ..")
        print_test_result(True, "Docker Image Built", "Image built successfully")
        return True
    except Exception as e:
        print_test_result(False, "Docker Image Built", str(e))
        return False

def test_docker_run():
    """Test Docker container run."""
    print("\n2. Testing Docker container run...")
    try:
        # Stop and remove any existing container
        run_command("docker stop consistency-manager-test", check_error=False)
        run_command("docker rm consistency-manager-test", check_error=False)
        
        # Start container with mock environment
        stdout, stderr = run_command(
            "docker run -d --name consistency-manager-test "
            "-e QUEUE_DB_URI=postgresql://test:test@localhost:5432/test_queue "
            "-e USER_PORTFOLIO_DB_URI=postgresql://test:test@localhost:5432/test_portfolio "
            "-e SYNC_INTERVAL=5 "
            "-e BATCH_SIZE=10 "
            "-p 8080:8080 "
            "consistency-manager-svc-test"
        )
        print_test_result(True, "Container Started", "Container started on port 8080")
        return True
    except Exception as e:
        print_test_result(False, "Container Started", str(e))
        return False

def test_health_endpoints():
    """Test health and readiness endpoints."""
    print("\n3. Testing health endpoints...")
    
    # Wait for container to start
    time.sleep(5)
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8080/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_test_result(True, "Health Endpoint", f"Status: {data.get('status')}")
        else:
            print_test_result(False, "Health Endpoint", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test_result(False, "Health Endpoint", str(e))
        return False
    
    try:
        # Test readiness endpoint
        response = requests.get("http://localhost:8080/ready", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_test_result(True, "Readiness Endpoint", f"Status: {data.get('status')}")
        else:
            print_test_result(False, "Readiness Endpoint", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test_result(False, "Readiness Endpoint", str(e))
        return False
    
    return True

def test_api_endpoints():
    """Test API endpoints."""
    print("\n4. Testing API endpoints...")
    
    try:
        # Test manual sync endpoint
        response = requests.post("http://localhost:8080/api/v1/sync", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_test_result(True, "Manual Sync Endpoint", f"Status: {data.get('status')}")
        else:
            print_test_result(False, "Manual Sync Endpoint", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test_result(False, "Manual Sync Endpoint", str(e))
        return False
    
    try:
        # Test stats endpoint
        response = requests.get("http://localhost:8080/api/v1/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print_test_result(True, "Stats Endpoint", "Stats retrieved successfully")
        else:
            print_test_result(False, "Stats Endpoint", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_test_result(False, "Stats Endpoint", str(e))
        return False
    
    return True

def test_container_logs():
    """Test container logs for errors."""
    print("\n5. Testing container logs...")
    
    try:
        stdout, stderr = run_command("docker logs consistency-manager-test")
        
        # Check for common error patterns
        error_patterns = [
            "ERROR",
            "Exception",
            "Traceback",
            "Failed to connect",
            "ModuleNotFoundError"
        ]
        
        errors_found = []
        for pattern in error_patterns:
            if pattern in stdout:
                errors_found.append(pattern)
        
        if errors_found:
            print_test_result(False, "Container Logs", f"Errors found: {errors_found}")
            print(f"    Log output: {stdout[-500:]}")  # Last 500 characters
            return False
        else:
            print_test_result(True, "Container Logs", "No errors found in logs")
            return True
    except Exception as e:
        print_test_result(False, "Container Logs", str(e))
        return False

def cleanup():
    """Clean up test containers."""
    print("\n6. Cleaning up...")
    try:
        run_command("docker stop consistency-manager-test", check_error=False)
        run_command("docker rm consistency-manager-test", check_error=False)
        print_test_result(True, "Cleanup", "Container stopped and removed")
    except Exception as e:
        print_test_result(False, "Cleanup", str(e))

def main():
    """Run all Docker-based tests."""
    print("🧪 Consistency Manager Service Docker Tests")
    print("=" * 60)
    
    test_results = []
    
    # Run tests
    test_results.append(("Docker Build", test_docker_build()))
    test_results.append(("Docker Run", test_docker_run()))
    test_results.append(("Health Endpoints", test_health_endpoints()))
    test_results.append(("API Endpoints", test_api_endpoints()))
    test_results.append(("Container Logs", test_container_logs()))
    
    # Cleanup
    cleanup()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Docker Test Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        if result:
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All Docker tests passed!")
        return True
    else:
        print("⚠️  Some Docker tests failed!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
