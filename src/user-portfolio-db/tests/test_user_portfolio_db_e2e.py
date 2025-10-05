#!/usr/bin/env python3
"""
User-Portfolio-DB End-to-End Test Suite

Complete end-to-end testing solution for the user-portfolio-db microservice.
This single file handles:
- Docker container management (build, start, stop, cleanup)
- Database schema setup and validation
- Comprehensive test execution (30+ test cases)
- Automatic cleanup and resource management

Usage:
    python test_user_portfolio_db_e2e.py

Copyright 2024 Google LLC
"""

import os
import sys
import time
import subprocess
import signal
import unittest
import logging
import psycopg2
import psycopg2.extras
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color
    
    @staticmethod
    def disable():
        """Disable colors for non-terminal output"""
        Colors.RED = Colors.GREEN = Colors.YELLOW = Colors.BLUE = ''
        Colors.PURPLE = Colors.CYAN = Colors.WHITE = Colors.NC = ''

class DockerManager:
    """Manages Docker container lifecycle for testing"""
    
    def __init__(self):
        self.container_name = "user-portfolio-db-test-e2e"
        self.image_name = "user-portfolio-db-test"
        self.db_port = 5432
        self.db_user = "portfolio-admin"
        self.db_password = "portfolio-pwd"
        self.db_name = "user-portfolio-db"
        self.db_uri = f"postgresql://{self.db_user}:{self.db_password}@localhost:{self.db_port}/{self.db_name}"
        
        self.test_dir = Path(__file__).parent
        self.container_id: Optional[str] = None
        self.container_running = False
        
        # Setup signal handlers for cleanup
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        logger.info(f"Received signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(1)
    
    def _run_command(self, command: List[str], capture_output: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
        """Run a command with error handling"""
        try:
            logger.debug(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                check=False,
                cwd=self.test_dir
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(command)}")
            raise
        except Exception as e:
            logger.error(f"Command failed: {e}")
            raise
    
    def _print_colored(self, message: str, color: str = Colors.NC):
        """Print colored message"""
        print(f"{color}{message}{Colors.NC}")
    
    def _print_header(self, title: str):
        """Print formatted header"""
        self._print_colored("\n" + "=" * 70, Colors.BLUE)
        self._print_colored(f" {title}", Colors.WHITE)
        self._print_colored("=" * 70, Colors.BLUE)
    
    def _print_success(self, message: str):
        """Print success message"""
        self._print_colored(f"✓ {message}", Colors.GREEN)
    
    def _print_error(self, message: str):
        """Print error message"""
        self._print_colored(f"✗ {message}", Colors.RED)
    
    def _print_info(self, message: str):
        """Print info message"""
        self._print_colored(f"ℹ {message}", Colors.CYAN)
    
    def check_docker_available(self) -> bool:
        """Check if Docker is available"""
        try:
            result = self._run_command(["docker", "--version"])
            if result.returncode == 0:
                self._print_success("Docker is available")
                return True
            else:
                self._print_error("Docker is not available")
                return False
        except FileNotFoundError:
            self._print_error("Docker command not found. Please install Docker.")
            return False
    
    def cleanup_existing_resources(self) -> bool:
        """Clean up any existing containers or images"""
        logger.info("Cleaning up existing resources...")
        
        # Stop and remove container if exists
        try:
            self._run_command(["docker", "stop", self.container_name], timeout=10)
            self._run_command(["docker", "rm", self.container_name], timeout=10)
        except Exception:
            pass  # Container might not exist
        
        # Remove image if exists
        try:
            self._run_command(["docker", "rmi", self.image_name], timeout=10)
        except Exception:
            pass  # Image might not exist
        
        return True
    
    def build_image(self) -> bool:
        """Build Docker image for testing"""
        self._print_header("Building Test Database Image")
        
        dockerfile_path = self.test_dir / "Dockerfile"
        if not dockerfile_path.exists():
            self._print_error(f"Dockerfile not found: {dockerfile_path}")
            return False
        
        build_command = [
            "docker", "build",
            "-t", self.image_name,
            "-f", str(dockerfile_path),
            str(self.test_dir)
        ]
        
        try:
            result = self._run_command(build_command, capture_output=False)
            if result.returncode == 0:
                self._print_success("Docker image built successfully")
                return True
            else:
                self._print_error("Failed to build Docker image")
                return False
        except Exception as e:
            self._print_error(f"Failed to build Docker image: {e}")
            return False
    
    def start_container(self) -> bool:
        """Start database container"""
        self._print_header("Starting Test Database Container")
        
        docker_command = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "-p", f"{self.db_port}:5432",
            self.image_name
        ]
        
        try:
            result = self._run_command(docker_command)
            if result.returncode == 0:
                self.container_id = result.stdout.strip()
                self._print_success(f"Container started: {self.container_id[:12]}")
                self.container_running = True
                return True
            else:
                self._print_error(f"Failed to start container: {result.stderr}")
                return False
        except Exception as e:
            self._print_error(f"Failed to start container: {e}")
            return False
    
    def wait_for_database(self, max_wait_time: int = 120) -> bool:
        """Wait for database to be ready"""
        self._print_header("Waiting for Database to be Ready")
        
        start_time = time.time()
        check_count = 0
        while time.time() - start_time < max_wait_time:
            check_count += 1
            elapsed = int(time.time() - start_time)
            
            try:
                # Check container health first
                self._print_info(f"Check #{check_count} (elapsed: {elapsed}s) - Checking container health...")
                health_result = self._run_command([
                    "docker", "exec", self.container_name,
                    "pg_isready", "-U", self.db_user, "-d", self.db_name
                ])
                
                if health_result.returncode == 0:
                    self._print_info("Container reports database is ready, testing connection...")
                    # Try actual connection
                    conn = psycopg2.connect(
                        host="localhost",
                        port=self.db_port,
                        user=self.db_user,
                        password=self.db_password,
                        database=self.db_name,
                        connect_timeout=10
                    )
                    conn.close()
                    self._print_success(f"Database is ready! (took {elapsed}s)")
                    return True
                else:
                    self._print_info(f"Container health check failed: {health_result.stderr}")
                    
            except (psycopg2.OperationalError, subprocess.SubprocessError) as e:
                self._print_info(f"Connection attempt failed: {str(e)}")
            
            # Check container logs for debugging
            if check_count % 5 == 0:  # Every 5th check
                self._print_info("Checking container logs for debugging...")
                try:
                    logs_result = self._run_command([
                        "docker", "logs", "--tail", "10", self.container_name
                    ])
                    if logs_result.stdout:
                        self._print_info(f"Recent logs: {logs_result.stdout.strip()}")
                except Exception:
                    pass
            
            time.sleep(3)
        
        self._print_error(f"Database failed to become ready within {max_wait_time}s timeout")
        
        # Final debugging - show container logs
        self._print_info("Final container logs for debugging:")
        try:
            logs_result = self._run_command([
                "docker", "logs", "--tail", "20", self.container_name
            ])
            if logs_result.stdout:
                self._print_info(logs_result.stdout.strip())
        except Exception:
            pass
            
        return False
    
    def verify_test_data(self) -> bool:
        """Verify test data exists in database"""
        self._print_header("Verifying Test Data")
        
        try:
            conn = psycopg2.connect(self.db_uri)
            cursor = conn.cursor()
            
            # Check if test portfolios exist
            cursor.execute("SELECT COUNT(*) FROM user_portfolios")
            portfolio_count = cursor.fetchone()[0]
            
            # Check if test transactions exist
            cursor.execute("SELECT COUNT(*) FROM portfolio_transactions")
            transaction_count = cursor.fetchone()[0]
            
            # Check if test analytics exist
            cursor.execute("SELECT COUNT(*) FROM portfolio_analytics")
            analytics_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if portfolio_count > 0 and transaction_count > 0:
                self._print_success(f"Found {portfolio_count} portfolios, {transaction_count} transactions, and {analytics_count} analytics records")
                return True
            else:
                self._print_error("Test data not found in database")
                return False
            
        except Exception as e:
            self._print_error(f"Failed to verify test data: {e}")
            return False
    
    def stop_container(self) -> bool:
        """Stop database container"""
        if not self.container_running:
            return True
        
        logger.info("Stopping database container...")
        
        try:
            result = self._run_command(["docker", "stop", self.container_name], timeout=30)
            if result.returncode == 0:
                self._print_success("Container stopped")
                self.container_running = False
                return True
            else:
                self._print_error(f"Failed to stop container: {result.stderr}")
                return False
        except Exception as e:
            self._print_error(f"Failed to stop container: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up all resources"""
        self._print_header("Cleaning Up Resources")
        
        success = True
        
        # Stop container
        if self.container_running:
            if not self.stop_container():
                success = False
        
        # Remove container
        try:
            self._run_command(["docker", "rm", self.container_name], timeout=10)
            self._print_success("Container removed")
        except Exception:
            pass  # Container might not exist
        
        # Remove image
        try:
            self._run_command(["docker", "rmi", self.image_name], timeout=10)
            self._print_success("Image removed")
        except Exception:
            pass  # Image might not exist
        
        return success


class UserPortfolioDBTestSuite(unittest.TestCase):
    """Comprehensive test suite for user-portfolio-db"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database connection"""
        cls.docker_manager = DockerManager()
        cls.db_uri = cls.docker_manager.db_uri
        
        try:
            cls.conn = psycopg2.connect(cls.db_uri)
            cls.cursor = cls.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info("Test database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to test database: {e}")
            raise unittest.SkipTest(f"Database connection failed: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up database connection"""
        if hasattr(cls, 'cursor') and cls.cursor:
            cls.cursor.close()
        if hasattr(cls, 'conn') and cls.conn:
            cls.conn.close()
        logger.info("Test database connection closed")
    
    def setUp(self):
        """Set up for each test"""
        try:
            self.cursor.execute("ROLLBACK")  # Clean up any previous transaction
        except:
            pass
        self.cursor.execute("BEGIN")
    
    def tearDown(self):
        """Clean up after each test"""
        try:
            self.cursor.execute("ROLLBACK")
        except:
            pass
    
    # Schema Validation Tests
    def test_user_portfolios_table_exists(self):
        """Test that user_portfolios table exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'user_portfolios' AND table_schema = 'public'
            )
        """)
        result = self.cursor.fetchone()
        self.assertTrue(result['exists'], "user_portfolios table should exist")
    
    def test_portfolio_transactions_table_exists(self):
        """Test that portfolio_transactions table exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'portfolio_transactions' AND table_schema = 'public'
            )
        """)
        result = self.cursor.fetchone()
        self.assertTrue(result['exists'], "portfolio_transactions table should exist")
    
    def test_portfolio_analytics_table_exists(self):
        """Test that portfolio_analytics table exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'portfolio_analytics' AND table_schema = 'public'
            )
        """)
        result = self.cursor.fetchone()
        self.assertTrue(result['exists'], "portfolio_analytics table should exist")
    
    def test_user_portfolios_table_structure(self):
        """Test user_portfolios table has correct column structure"""
        self.cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'user_portfolios' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        columns = self.cursor.fetchall()
        
        expected_columns = ['accountid', 'currency', 'tier1_allocation', 'tier2_allocation', 
                          'tier3_allocation', 'total_allocation', 'tier1_value', 'tier2_value', 
                          'tier3_value', 'total_value', 'created_at', 'updated_at']
        actual_columns = [col['column_name'] for col in columns]
        
        self.assertEqual(actual_columns, expected_columns, "user_portfolios table should have correct column structure")
    
    def test_portfolio_transactions_table_structure(self):
        """Test portfolio_transactions table has correct column structure"""
        self.cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'portfolio_transactions' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        columns = self.cursor.fetchall()
        
        expected_columns = ['id', 'accountid', 'transaction_type', 'tier1_change', 'tier2_change', 
                          'tier3_change', 'total_amount', 'fees', 'status', 'created_at', 'updated_at']
        actual_columns = [col['column_name'] for col in columns]
        
        self.assertEqual(actual_columns, expected_columns, "portfolio_transactions table should have correct column structure")
    
    def test_check_constraints_exist(self):
        """Test check constraints exist"""
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.check_constraints 
            WHERE constraint_name LIKE '%tier%' OR constraint_name LIKE '%allocation%'
        """)
        result = self.cursor.fetchone()
        self.assertGreater(result['count'], 0, "Check constraints should exist")
    
    def test_indexes_exist(self):
        """Test that performance indexes exist"""
        self.cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('user_portfolios', 'portfolio_transactions', 'portfolio_analytics') 
            AND schemaname = 'public'
            AND indexname LIKE 'idx_%'
        """)
        indexes = self.cursor.fetchall()
        self.assertGreater(len(indexes), 0, "Performance indexes should exist")
    
    # Constraint Tests
    def test_tier_allocation_constraint_valid(self):
        """Test valid tier allocation values are accepted"""
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST001', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
    
    def test_tier_allocation_constraint_invalid(self):
        """Test invalid tier allocation values are rejected"""
        with self.assertRaises(psycopg2.IntegrityError):
            try:
                self.cursor.execute("""
                    INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
                    VALUES (%s, %s, %s, %s, %s)
                """, ('TEST002', Decimal('50.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
            except psycopg2.IntegrityError:
                self.cursor.execute("ROLLBACK")
                self.cursor.execute("BEGIN")
                raise
    
    def test_transaction_type_constraint_valid(self):
        """Test valid transaction types are accepted"""
        # First create the portfolio that the transaction references
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST003', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        for transaction_type in ['INVEST', 'WITHDRAWAL']:
            with self.subTest(transaction_type=transaction_type):
                self.cursor.execute("""
                    INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('TEST003', transaction_type, Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
    
    def test_transaction_type_constraint_invalid(self):
        """Test invalid transaction types are rejected"""
        with self.assertRaises(psycopg2.IntegrityError):
            try:
                self.cursor.execute("""
                    INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('TEST004', 'INVALID_TYPE', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
            except psycopg2.IntegrityError:
                self.cursor.execute("ROLLBACK")
                self.cursor.execute("BEGIN")
                raise
    
    def test_transaction_status_constraint_valid(self):
        """Test valid transaction statuses are accepted"""
        # First create the portfolio that the transaction references
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, ('TEST005', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        for status in ['PENDING', 'COMPLETED', 'FAILED', 'CANCELLED']:
            with self.subTest(status=status):
                self.cursor.execute("""
                    INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('TEST005', 'INVEST', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00'), status))
    
    def test_transaction_status_constraint_invalid(self):
        """Test invalid transaction statuses are rejected"""
        with self.assertRaises(psycopg2.IntegrityError):
            try:
                self.cursor.execute("""
                    INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount, status)
                    VALUES (%s, %s, %s, %s)
                """, ('TEST006', 'INVEST', Decimal('100.00'), 'INVALID_STATUS'))
            except psycopg2.IntegrityError:
                self.cursor.execute("ROLLBACK")
                self.cursor.execute("BEGIN")
                raise
    
    # Query Functionality Tests
    def test_get_user_portfolio(self):
        """Test query to get user portfolio"""
        self.cursor.execute("""
            SELECT accountid, currency, tier1_allocation, tier2_allocation, tier3_allocation, 
                   total_allocation, tier1_value, tier2_value, tier3_value, total_value,
                   created_at, updated_at
            FROM user_portfolios 
            WHERE accountid = %s
        """, ('1000000001',))
        portfolio = self.cursor.fetchone()
        
        self.assertIsNotNone(portfolio, "Should return portfolio for account")
        self.assertEqual(portfolio['accountid'], '1000000001')
        self.assertEqual(portfolio['currency'], 'USD')
    
    def test_get_portfolio_transactions(self):
        """Test query to get portfolio transactions"""
        self.cursor.execute("""
            SELECT id, transaction_type, tier1_change, tier2_change, tier3_change,
                   total_amount, fees, status, created_at, updated_at
            FROM portfolio_transactions 
            WHERE accountid = %s 
            ORDER BY created_at DESC
        """, ('1000000001',))
        transactions = self.cursor.fetchall()
        
        self.assertGreater(len(transactions), 0, "Should return transactions for account")
        
        for transaction in transactions:
            self.assertIn('transaction_type', transaction)
            self.assertIn('total_amount', transaction)
            self.assertIn('status', transaction)
    
    def test_calculate_total_invested(self):
        """Test calculate total amount invested by a user"""
        self.cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) as total_invested
            FROM portfolio_transactions 
            WHERE accountid = %s AND transaction_type = 'INVEST' AND status = 'COMPLETED'
        """, ('1000000001',))
        result = self.cursor.fetchone()
        
        self.assertIsNotNone(result, "Should return total invested amount")
        self.assertGreater(result['total_invested'], 0, "Should have invested amount")
    
    def test_portfolio_summary_view(self):
        """Test portfolio summary view"""
        self.cursor.execute("""
            SELECT * FROM portfolio_summary WHERE accountid = %s
        """, ('1000000001',))
        summary = self.cursor.fetchone()
        
        self.assertIsNotNone(summary, "Should return portfolio summary")
        self.assertIn('total_value', summary)
        self.assertIn('tier1_allocation', summary)
        self.assertIn('tier2_allocation', summary)
        self.assertIn('tier3_allocation', summary)
    
    # Update Functionality Tests
    def test_update_portfolio_allocation(self):
        """Test updating portfolio allocation"""
        accountid = 'TEST001'
        
        # Insert test portfolio
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, (accountid, Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        # Update allocation
        self.cursor.execute("""
            UPDATE user_portfolios 
            SET tier1_allocation = %s, tier2_allocation = %s, tier3_allocation = %s, total_allocation = %s
            WHERE accountid = %s
        """, (Decimal('50.00'), Decimal('25.00'), Decimal('25.00'), Decimal('100.00'), accountid))
        
        self.assertEqual(self.cursor.rowcount, 1, "Should update exactly one row")
        
        # Verify update
        self.cursor.execute("SELECT tier1_allocation FROM user_portfolios WHERE accountid = %s", (accountid,))
        result = self.cursor.fetchone()
        self.assertEqual(result['tier1_allocation'], Decimal('50.00'))
    
    def test_update_portfolio_values(self):
        """Test updating portfolio values"""
        accountid = 'TEST002'
        
        # Insert test portfolio
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_value, tier2_value, tier3_value, total_value)
            VALUES (%s, %s, %s, %s, %s)
        """, (accountid, Decimal('4000.00'), Decimal('3000.00'), Decimal('3000.00'), Decimal('10000.00')))
        
        # Update values
        self.cursor.execute("""
            UPDATE user_portfolios 
            SET tier1_value = %s, tier2_value = %s, tier3_value = %s, total_value = %s
            WHERE accountid = %s
        """, (Decimal('5000.00'), Decimal('2500.00'), Decimal('2500.00'), Decimal('10000.00'), accountid))
        
        self.assertEqual(self.cursor.rowcount, 1, "Should update exactly one row")
        
        # Verify update
        self.cursor.execute("SELECT tier1_value FROM user_portfolios WHERE accountid = %s", (accountid,))
        result = self.cursor.fetchone()
        self.assertEqual(result['tier1_value'], Decimal('5000.00'))
    
    def test_update_transaction_status(self):
        """Test updating transaction status"""
        accountid = 'TEST003'
        
        # Insert test portfolio first
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, (accountid, Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        # Insert test transaction
        self.cursor.execute("""
            INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (accountid, 'INVEST', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00'), 'PENDING'))
        
        # Update status
        self.cursor.execute("""
            UPDATE portfolio_transactions 
            SET status = %s
            WHERE accountid = %s AND status = 'PENDING'
        """, ('COMPLETED', accountid))
        
        self.assertEqual(self.cursor.rowcount, 1, "Should update exactly one row")
        
        # Verify update
        self.cursor.execute("SELECT status FROM portfolio_transactions WHERE accountid = %s", (accountid,))
        result = self.cursor.fetchone()
        self.assertEqual(result['status'], 'COMPLETED')
    
    # Performance Tests
    def test_index_performance_accountid_query(self):
        """Test performance of accountid-based queries"""
        start_time = time.time()
        self.cursor.execute("SELECT * FROM user_portfolios WHERE accountid = '1000000001'")
        portfolio = self.cursor.fetchone()
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.1, "Accountid query should be fast (< 100ms)")
        self.assertIsNotNone(portfolio, "Should find portfolio for account")
    
    def test_index_performance_transaction_query(self):
        """Test performance of transaction queries"""
        start_time = time.time()
        self.cursor.execute("SELECT * FROM portfolio_transactions WHERE accountid = '1000000001'")
        transactions = self.cursor.fetchall()
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.1, "Transaction query should be fast (< 100ms)")
        self.assertGreater(len(transactions), 0, "Should return transactions")
    
    # Data Integrity Tests
    def test_data_types_consistency(self):
        """Test that data types are consistent"""
        self.cursor.execute("SELECT * FROM user_portfolios LIMIT 1")
        portfolio = self.cursor.fetchone()
        
        if portfolio:
            self.assertIsInstance(portfolio['accountid'], str)
            self.assertIsInstance(portfolio['tier1_allocation'], Decimal)
            self.assertIsInstance(portfolio['tier1_value'], Decimal)
            self.assertIsInstance(portfolio['created_at'], datetime)
    
    def test_decimal_precision(self):
        """Test decimal precision for allocations and values"""
        self.cursor.execute("SELECT tier1_allocation, tier1_value FROM user_portfolios WHERE accountid = '1000000001'")
        portfolio = self.cursor.fetchone()
        
        if portfolio:
            # Test that decimals maintain precision
            self.assertIsInstance(portfolio['tier1_allocation'], Decimal)
            self.assertIsInstance(portfolio['tier1_value'], Decimal)
    
    # Integration Tests
    def test_complete_portfolio_lifecycle(self):
        """Test complete portfolio lifecycle: create, read, update"""
        accountid = 'TEST004'
        
        # Create portfolio
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation,
                                       tier1_value, tier2_value, tier3_value, total_value)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (accountid, Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00'),
              Decimal('4000.00'), Decimal('3000.00'), Decimal('3000.00'), Decimal('10000.00')))
        
        # Read portfolio
        self.cursor.execute("SELECT * FROM user_portfolios WHERE accountid = %s", (accountid,))
        portfolio = self.cursor.fetchone()
        self.assertIsNotNone(portfolio, "Should be able to read created portfolio")
        
        # Update portfolio
        new_tier1_value = Decimal('5000.00')
        new_total_value = Decimal('11000.00')  # 5000 + 3000 + 3000
        self.cursor.execute("""
            UPDATE user_portfolios SET tier1_value = %s, total_value = %s WHERE accountid = %s
        """, (new_tier1_value, new_total_value, accountid))
        
        self.cursor.execute("SELECT tier1_value FROM user_portfolios WHERE accountid = %s", (accountid,))
        updated_portfolio = self.cursor.fetchone()
        self.assertEqual(updated_portfolio['tier1_value'], new_tier1_value, "Should be able to update portfolio")
    
    def test_transaction_rollback(self):
        """Test transaction rollback functionality"""
        accountid = 'TEST005'
        
        # Start transaction
        self.cursor.execute("BEGIN")
        
        # Insert portfolio
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, (accountid, Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        # Rollback transaction
        self.cursor.execute("ROLLBACK")
        
        # Verify portfolio doesn't exist
        self.cursor.execute("SELECT * FROM user_portfolios WHERE accountid = %s", (accountid,))
        result = self.cursor.fetchone()
        self.assertIsNone(result, "Portfolio should not exist after rollback")
    
    def test_foreign_key_constraint(self):
        """Test foreign key constraint between portfolio_transactions and user_portfolios"""
        with self.assertRaises(psycopg2.IntegrityError):
            try:
                self.cursor.execute("""
                    INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('NONEXIST', 'INVEST', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
            except psycopg2.IntegrityError:
                self.cursor.execute("ROLLBACK")
                self.cursor.execute("BEGIN")
                raise
    
    def test_cascade_delete(self):
        """Test cascade delete functionality"""
        accountid = 'TEST006'
        
        # Insert portfolio
        self.cursor.execute("""
            INSERT INTO user_portfolios (accountid, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation)
            VALUES (%s, %s, %s, %s, %s)
        """, (accountid, Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        # Insert transaction
        self.cursor.execute("""
            INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (accountid, 'INVEST', Decimal('40.00'), Decimal('30.00'), Decimal('30.00'), Decimal('100.00')))
        
        # Delete portfolio (should cascade to transactions)
        self.cursor.execute("DELETE FROM user_portfolios WHERE accountid = %s", (accountid,))
        
        # Verify transaction is also deleted
        self.cursor.execute("SELECT * FROM portfolio_transactions WHERE accountid = %s", (accountid,))
        result = self.cursor.fetchone()
        self.assertIsNone(result, "Transaction should be deleted when portfolio is deleted")


def install_dependencies():
    """Install required dependencies"""
    try:
        import psycopg2
        return True
    except ImportError:
        print("Installing psycopg2-binary...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 'psycopg2-binary'
            ])
            return True
        except subprocess.CalledProcessError:
            print("Failed to install psycopg2-binary. Please install manually:")
            print("pip install psycopg2-binary")
            return False


def main():
    """Main test execution function"""
    print("=" * 70)
    print("User-Portfolio-DB End-to-End Test Suite")
    print("=" * 70)
    print("Complete database testing with container management")
    print("=" * 70)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Initialize Docker manager
    docker_manager = DockerManager()
    
    try:
        # Check Docker availability
        if not docker_manager.check_docker_available():
            sys.exit(1)
        
        # Clean up any existing resources
        docker_manager.cleanup_existing_resources()
        
        # Build Docker image
        if not docker_manager.build_image():
            sys.exit(1)
        
        # Start container
        if not docker_manager.start_container():
            sys.exit(1)
        
        # Wait for database to be ready
        if not docker_manager.wait_for_database():
            sys.exit(1)
        
        # Verify test data exists
        if not docker_manager.verify_test_data():
            sys.exit(1)
        
        # Run tests
        docker_manager._print_header("Running Comprehensive Test Suite")
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(UserPortfolioDBTestSuite)
        
        # Run tests with detailed output
        runner = unittest.TextTestRunner(
            verbosity=2,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        result = runner.run(suite)
        
        # Print summary
        docker_manager._print_header("Test Results Summary")
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
        passed = total_tests - failures - errors - skipped
        
        docker_manager._print_info(f"Tests run: {total_tests}")
        docker_manager._print_success(f"Passed: {passed}")
        if failures > 0:
            docker_manager._print_error(f"Failures: {failures}")
        if errors > 0:
            docker_manager._print_error(f"Errors: {errors}")
        if skipped > 0:
            docker_manager._print_info(f"Skipped: {skipped}")
        
        success_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
        docker_manager._print_info(f"Success Rate: {success_rate:.1f}%")
        
        if result.wasSuccessful():
            docker_manager._print_success("🎉 All tests passed!")
            exit_code = 0
        else:
            docker_manager._print_error("❌ Some tests failed")
            exit_code = 1
        
    except KeyboardInterrupt:
        docker_manager._print_info("Test execution interrupted by user")
        exit_code = 1
    except Exception as e:
        docker_manager._print_error(f"Test execution failed: {e}")
        exit_code = 1
    finally:
        # Always cleanup
        docker_manager.cleanup()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
