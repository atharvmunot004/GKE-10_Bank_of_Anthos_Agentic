"""
Script to run load tests with different scenarios
"""

import subprocess
import time
import os
from typing import List, Dict, Any


class LoadTestRunner:
    """Load test runner for different scenarios"""
    
    def __init__(self, host: str = "http://localhost:8080"):
        self.host = host
        self.results_dir = "load_test_results"
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run_normal_load_test(self, users: int = 100, spawn_rate: int = 10, duration: str = "10m"):
        """Run normal load test"""
        print(f"Running normal load test: {users} users, {duration}")
        
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", duration,
            "--headless",
            "--html", f"{self.results_dir}/normal_load_test.html",
            "--csv", f"{self.results_dir}/normal_load_test"
        ]
        
        return self._run_command(cmd)
    
    def run_peak_load_test(self, users: int = 500, spawn_rate: int = 50, duration: str = "10m"):
        """Run peak load test"""
        print(f"Running peak load test: {users} users, {duration}")
        
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", duration,
            "--headless",
            "--html", f"{self.results_dir}/peak_load_test.html",
            "--csv", f"{self.results_dir}/peak_load_test"
        ]
        
        return self._run_command(cmd)
    
    def run_stress_test(self, users: int = 1000, spawn_rate: int = 100, duration: str = "10m"):
        """Run stress test"""
        print(f"Running stress test: {users} users, {duration}")
        
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", duration,
            "--headless",
            "--html", f"{self.results_dir}/stress_test.html",
            "--csv", f"{self.results_dir}/stress_test"
        ]
        
        return self._run_command(cmd)
    
    def run_high_load_test(self, users: int = 200, spawn_rate: int = 20, duration: str = "5m"):
        """Run high load test using HighLoadUser"""
        print(f"Running high load test: {users} users, {duration}")
        
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "HighLoadUser",
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", duration,
            "--headless",
            "--html", f"{self.results_dir}/high_load_test.html",
            "--csv", f"{self.results_dir}/high_load_test"
        ]
        
        return self._run_command(cmd)
    
    def run_spike_test(self, users: int = 300, spawn_rate: int = 100, duration: str = "5m"):
        """Run spike test using SpikeTestUser"""
        print(f"Running spike test: {users} users, {duration}")
        
        cmd = [
            "locust",
            "-f", "locustfile.py",
            "SpikeTestUser",
            "--host", self.host,
            "--users", str(users),
            "--spawn-rate", str(spawn_rate),
            "--run-time", duration,
            "--headless",
            "--html", f"{self.results_dir}/spike_test.html",
            "--csv", f"{self.results_dir}/spike_test"
        ]
        
        return self._run_command(cmd)
    
    def run_all_tests(self):
        """Run all load test scenarios"""
        print("Starting comprehensive load testing...")
        
        tests = [
            ("Normal Load", lambda: self.run_normal_load_test()),
            ("Peak Load", lambda: self.run_peak_load_test()),
            ("Stress Test", lambda: self.run_stress_test()),
            ("High Load", lambda: self.run_high_load_test()),
            ("Spike Test", lambda: self.run_spike_test())
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n{'='*50}")
            print(f"Running {test_name} Test")
            print(f"{'='*50}")
            
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            results.append({
                "test_name": test_name,
                "success": result.returncode == 0,
                "duration": end_time - start_time,
                "return_code": result.returncode
            })
            
            if result.returncode == 0:
                print(f"✅ {test_name} test completed successfully")
            else:
                print(f"❌ {test_name} test failed with return code {result.returncode}")
            
            # Wait between tests
            print("Waiting 30 seconds before next test...")
            time.sleep(30)
        
        # Print summary
        print(f"\n{'='*50}")
        print("Load Testing Summary")
        print(f"{'='*50}")
        
        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{result['test_name']:20} {status:10} ({result['duration']:.1f}s)")
        
        return results
    
    def _run_command(self, cmd: List[str]) -> subprocess.CompletedProcess:
        """Run a command and return the result"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            
            return result
            
        except subprocess.TimeoutExpired:
            print("Command timed out after 30 minutes")
            return subprocess.CompletedProcess(cmd, -1, "", "Timeout")
        except Exception as e:
            print(f"Error running command: {e}")
            return subprocess.CompletedProcess(cmd, -1, "", str(e))


def main():
    """Main function to run load tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run load tests for User Tier Agent")
    parser.add_argument("--host", default="http://localhost:8080", help="Target host")
    parser.add_argument("--test", choices=["normal", "peak", "stress", "high", "spike", "all"], 
                       default="all", help="Test to run")
    parser.add_argument("--users", type=int, default=100, help="Number of users")
    parser.add_argument("--spawn-rate", type=int, default=10, help="User spawn rate")
    parser.add_argument("--duration", default="10m", help="Test duration")
    
    args = parser.parse_args()
    
    runner = LoadTestRunner(args.host)
    
    if args.test == "normal":
        runner.run_normal_load_test(args.users, args.spawn_rate, args.duration)
    elif args.test == "peak":
        runner.run_peak_load_test(args.users, args.spawn_rate, args.duration)
    elif args.test == "stress":
        runner.run_stress_test(args.users, args.spawn_rate, args.duration)
    elif args.test == "high":
        runner.run_high_load_test(args.users, args.spawn_rate, args.duration)
    elif args.test == "spike":
        runner.run_spike_test(args.users, args.spawn_rate, args.duration)
    elif args.test == "all":
        runner.run_all_tests()


if __name__ == "__main__":
    main()
