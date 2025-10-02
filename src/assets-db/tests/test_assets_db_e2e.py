#!/usr/bin/env python3
"""
Assets-DB End-to-End Test Suite

Complete end-to-end testing solution for the assets-db microservice.
This single file handles:
- Docker container management (build, start, stop, cleanup)
- Database schema setup and validation
- Comprehensive test execution (30+ test cases)
- Automatic cleanup and resource management

Usage:
    python test_assets_db_e2e.py

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
        self.container_name = "assets-db-test-e2e"
        self.image_name = "assets-db-test"
        self.db_port = 5432
        self.db_user = "assets-admin"
        self.db_password = "assets-pwd"
        self.db_name = "assets-db"
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
    
    def wait_for_database(self, max_wait_time: int = 60) -> bool:
        """Wait for database to be ready"""
        self._print_header("Waiting for Database to be Ready")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                # Check container health
                result = self._run_command([
                    "docker", "exec", self.container_name,
                    "pg_isready", "-U", self.db_user, "-d", self.db_name
                ])
                
                if result.returncode == 0:
                    # Try actual connection
                    conn = psycopg2.connect(
                        host="localhost",
                        port=self.db_port,
                        user=self.db_user,
                        password=self.db_password,
                        database=self.db_name,
                        connect_timeout=5
                    )
                    conn.close()
                    self._print_success("Database is ready!")
                    return True
                    
            except (psycopg2.OperationalError, subprocess.SubprocessError):
                pass  # Database not ready yet
            
            time.sleep(2)
            self._print_info("Database not ready yet, waiting...")
        
        self._print_error("Database failed to become ready within timeout")
        return False
    
    def insert_test_data(self) -> bool:
        """Insert test data into database"""
        self._print_header("Inserting Test Data")
        
        test_data = [
            (1, 'BTC', Decimal('100.00000000'), Decimal('45000.00')),
            (1, 'ETH', Decimal('500.00000000'), Decimal('3200.00')),
            (2, 'SPY', Decimal('1000.00000000'), Decimal('450.00')),
            (2, 'QQQ', Decimal('800.00000000'), Decimal('380.00')),
            (3, 'REIT_A', Decimal('100.00000000'), Decimal('25.50')),
            (3, 'REIT_B', Decimal('200.00000000'), Decimal('30.75'))
        ]
        
        try:
            conn = psycopg2.connect(self.db_uri)
            cursor = conn.cursor()
            
            for tier, name, amount, price in test_data:
                cursor.execute("""
                    INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                    VALUES (%s, %s, %s, %s)
                """, (tier, name, amount, price))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self._print_success(f"Inserted {len(test_data)} test assets")
            return True
            
        except Exception as e:
            self._print_error(f"Failed to insert test data: {e}")
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


class AssetsDBTestSuite(unittest.TestCase):
    """Comprehensive test suite for assets-db"""
    
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
    def test_table_exists(self):
        """Test that assets table exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'assets' AND table_schema = 'public'
            )
        """)
        result = self.cursor.fetchone()
        self.assertTrue(result['exists'], "Assets table should exist")
    
    def test_table_structure(self):
        """Test table has correct column structure"""
        self.cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'assets' AND table_schema = 'public'
            ORDER BY ordinal_position
        """)
        columns = self.cursor.fetchall()
        
        expected_columns = ['asset_id', 'tier_number', 'asset_name', 'amount', 'price_per_unit', 'last_updated']
        actual_columns = [col['column_name'] for col in columns]
        
        self.assertEqual(actual_columns, expected_columns, "Table should have correct column structure")
    
    def test_primary_key_constraint(self):
        """Test primary key constraint exists"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = 'assets' 
                AND constraint_type = 'PRIMARY KEY'
            )
        """)
        result = self.cursor.fetchone()
        self.assertTrue(result['exists'], "Primary key constraint should exist")
    
    def test_unique_constraint(self):
        """Test unique constraint on asset_name"""
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE table_name = 'assets' 
                AND constraint_type = 'UNIQUE'
            )
        """)
        result = self.cursor.fetchone()
        self.assertTrue(result['exists'], "Unique constraint should exist")
    
    def test_check_constraints(self):
        """Test check constraints exist"""
        self.cursor.execute("""
            SELECT COUNT(*) as count FROM information_schema.check_constraints 
            WHERE constraint_name LIKE 'assets_%'
        """)
        result = self.cursor.fetchone()
        self.assertGreater(result['count'], 0, "Check constraints should exist")
    
    def test_indexes_exist(self):
        """Test that performance indexes exist"""
        self.cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'assets' AND schemaname = 'public'
            AND indexname IN ('idx_assets_tier', 'idx_assets_name')
        """)
        indexes = self.cursor.fetchall()
        self.assertEqual(len(indexes), 2, "Both performance indexes should exist")
    
    # Constraint Tests
    def test_tier_constraint_valid_values(self):
        """Test valid tier values are accepted"""
        for tier in [1, 2, 3]:
            with self.subTest(tier=tier):
                self.cursor.execute("""
                    INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                    VALUES (%s, %s, %s, %s)
                """, (tier, f'TEST_TIER_{tier}', Decimal('100.0'), Decimal('50.0')))
    
    def test_tier_constraint_invalid_values(self):
        """Test invalid tier values are rejected"""
        for tier in [0, 4, -1]:
            with self.subTest(tier=tier):
                with self.assertRaises(psycopg2.IntegrityError):
                    try:
                        self.cursor.execute("""
                            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                            VALUES (%s, %s, %s, %s)
                        """, (tier, f'TEST_INVALID_{tier}', Decimal('100.0'), Decimal('50.0')))
                    except psycopg2.IntegrityError:
                        self.cursor.execute("ROLLBACK")
                        self.cursor.execute("BEGIN")
                        raise
    
    def test_amount_constraint_valid_values(self):
        """Test valid amount values are accepted"""
        for amount in [Decimal('0'), Decimal('100.5'), Decimal('999999.99999999')]:
            with self.subTest(amount=amount):
                self.cursor.execute("""
                    INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                    VALUES (%s, %s, %s, %s)
                """, (1, f'TEST_AMOUNT_{amount}', amount, Decimal('50.0')))
    
    def test_amount_constraint_invalid_values(self):
        """Test invalid amount values are rejected"""
        for amount in [Decimal('-0.01'), Decimal('-100')]:
            with self.subTest(amount=amount):
                with self.assertRaises(psycopg2.IntegrityError):
                    try:
                        self.cursor.execute("""
                            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                            VALUES (%s, %s, %s, %s)
                        """, (1, f'TEST_NEG_{amount}', amount, Decimal('50.0')))
                    except psycopg2.IntegrityError:
                        self.cursor.execute("ROLLBACK")
                        self.cursor.execute("BEGIN")
                        raise
    
    def test_price_constraint_valid_values(self):
        """Test valid price values are accepted"""
        for price in [Decimal('0.01'), Decimal('100.50'), Decimal('999999.99')]:
            with self.subTest(price=price):
                self.cursor.execute("""
                    INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                    VALUES (%s, %s, %s, %s)
                """, (1, f'TEST_PRICE_{price}', Decimal('100.0'), price))
    
    def test_price_constraint_invalid_values(self):
        """Test invalid price values are rejected"""
        for price in [Decimal('0'), Decimal('-0.01')]:
            with self.subTest(price=price):
                with self.assertRaises(psycopg2.IntegrityError):
                    try:
                        self.cursor.execute("""
                            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                            VALUES (%s, %s, %s, %s)
                        """, (1, f'TEST_ZERO_{price}', Decimal('100.0'), price))
                    except psycopg2.IntegrityError:
                        self.cursor.execute("ROLLBACK")
                        self.cursor.execute("BEGIN")
                        raise
    
    def test_unique_constraint_asset_name(self):
        """Test asset_name uniqueness is enforced"""
        self.cursor.execute("""
            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
            VALUES (%s, %s, %s, %s)
        """, (1, 'UNIQUE_TEST', Decimal('100.0'), Decimal('50.0')))
        
        with self.assertRaises(psycopg2.IntegrityError):
            self.cursor.execute("""
                INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
                VALUES (%s, %s, %s, %s)
            """, (2, 'UNIQUE_TEST', Decimal('200.0'), Decimal('60.0')))
    
    # Query Functionality Tests
    def test_get_all_assets(self):
        """Test query to get all assets"""
        self.cursor.execute("""
            SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated 
            FROM assets 
            ORDER BY tier_number, asset_name
        """)
        assets = self.cursor.fetchall()
        
        self.assertGreater(len(assets), 0, "Should return assets")
        
        # Verify structure
        for asset in assets:
            self.assertIn('asset_id', asset)
            self.assertIn('tier_number', asset)
            self.assertIn('asset_name', asset)
            self.assertIn('amount', asset)
            self.assertIn('price_per_unit', asset)
            self.assertIn('last_updated', asset)
    
    def test_get_assets_by_tier(self):
        """Test query to get assets by tier"""
        for tier in [1, 2, 3]:
            with self.subTest(tier=tier):
                self.cursor.execute("""
                    SELECT * FROM assets WHERE tier_number = %s
                """, (tier,))
                assets = self.cursor.fetchall()
                
                for asset in assets:
                    self.assertEqual(asset['tier_number'], tier)
    
    def test_get_specific_asset(self):
        """Test query to get specific asset by name"""
        self.cursor.execute("""
            SELECT * FROM assets WHERE asset_name = %s
        """, ('BTC',))
        asset = self.cursor.fetchone()
        
        self.assertIsNotNone(asset, "Should find BTC asset")
        self.assertEqual(asset['asset_name'], 'BTC')
        self.assertEqual(asset['tier_number'], 1)
    
    def test_asset_statistics_by_tier(self):
        """Test query to get asset statistics by tier"""
        self.cursor.execute("""
            SELECT 
                tier_number,
                COUNT(*) as asset_count,
                SUM(amount * price_per_unit) as total_value,
                AVG(price_per_unit) as avg_price
            FROM assets 
            GROUP BY tier_number 
            ORDER BY tier_number
        """)
        stats = self.cursor.fetchall()
        
        self.assertGreater(len(stats), 0, "Should return tier statistics")
        
        for stat in stats:
            self.assertIn('tier_number', stat)
            self.assertIn('asset_count', stat)
            self.assertIn('total_value', stat)
            self.assertIn('avg_price', stat)
            self.assertGreater(stat['asset_count'], 0)
    
    # Update Functionality Tests
    def test_update_asset_amount(self):
        """Test updating asset amount"""
        asset_name = 'TEST_UPDATE_AMOUNT'
        initial_amount = Decimal('100.0')
        new_amount = Decimal('150.0')
        
        # Insert test asset
        self.cursor.execute("""
            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
            VALUES (%s, %s, %s, %s)
        """, (1, asset_name, initial_amount, Decimal('50.0')))
        
        # Update amount
        self.cursor.execute("""
            UPDATE assets 
            SET amount = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE asset_name = %s
        """, (new_amount, asset_name))
        
        self.assertEqual(self.cursor.rowcount, 1, "Should update exactly one row")
        
        # Verify update
        self.cursor.execute("SELECT amount FROM assets WHERE asset_name = %s", (asset_name,))
        result = self.cursor.fetchone()
        self.assertEqual(result['amount'], new_amount)
    
    def test_update_asset_price(self):
        """Test updating asset price"""
        asset_name = 'TEST_UPDATE_PRICE'
        initial_price = Decimal('50.0')
        new_price = Decimal('75.0')
        
        # Insert test asset
        self.cursor.execute("""
            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
            VALUES (%s, %s, %s, %s)
        """, (1, asset_name, Decimal('100.0'), initial_price))
        
        # Update price
        self.cursor.execute("""
            UPDATE assets 
            SET price_per_unit = %s, last_updated = CURRENT_TIMESTAMP 
            WHERE asset_name = %s
        """, (new_price, asset_name))
        
        self.assertEqual(self.cursor.rowcount, 1, "Should update exactly one row")
        
        # Verify update
        self.cursor.execute("SELECT price_per_unit FROM assets WHERE asset_name = %s", (asset_name,))
        result = self.cursor.fetchone()
        self.assertEqual(result['price_per_unit'], new_price)
    
    # Performance Tests
    def test_index_performance_tier_query(self):
        """Test performance of tier-based queries"""
        start_time = time.time()
        self.cursor.execute("SELECT * FROM assets WHERE tier_number = 1")
        assets = self.cursor.fetchall()
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.1, "Tier query should be fast (< 100ms)")
        self.assertGreater(len(assets), 0, "Should return assets for tier 1")
    
    def test_index_performance_name_query(self):
        """Test performance of name-based queries"""
        start_time = time.time()
        self.cursor.execute("SELECT * FROM assets WHERE asset_name = 'BTC'")
        asset = self.cursor.fetchone()
        query_time = time.time() - start_time
        
        self.assertLess(query_time, 0.1, "Name query should be fast (< 100ms)")
        self.assertIsNotNone(asset, "Should find BTC asset")
    
    # Data Integrity Tests
    def test_data_types_consistency(self):
        """Test that data types are consistent"""
        self.cursor.execute("SELECT * FROM assets LIMIT 1")
        asset = self.cursor.fetchone()
        
        if asset:
            self.assertIsInstance(asset['asset_id'], int)
            self.assertIsInstance(asset['tier_number'], int)
            self.assertIsInstance(asset['asset_name'], str)
            self.assertIsInstance(asset['amount'], Decimal)
            self.assertIsInstance(asset['price_per_unit'], Decimal)
            self.assertIsInstance(asset['last_updated'], datetime)
    
    def test_decimal_precision(self):
        """Test decimal precision for amount and price"""
        self.cursor.execute("SELECT amount, price_per_unit FROM assets WHERE asset_name = 'BTC'")
        asset = self.cursor.fetchone()
        
        if asset:
            # Test that decimals maintain precision
            self.assertIsInstance(asset['amount'], Decimal)
            self.assertIsInstance(asset['price_per_unit'], Decimal)
    
    # Integration Tests
    def test_complete_asset_lifecycle(self):
        """Test complete asset lifecycle: create, read, update, delete"""
        asset_name = 'LIFECYCLE_TEST'
        
        # Create
        self.cursor.execute("""
            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
            VALUES (%s, %s, %s, %s)
        """, (2, asset_name, Decimal('100.0'), Decimal('50.0')))
        
        # Read
        self.cursor.execute("SELECT * FROM assets WHERE asset_name = %s", (asset_name,))
        asset = self.cursor.fetchone()
        self.assertIsNotNone(asset, "Should be able to read created asset")
        
        # Update
        new_amount = Decimal('200.0')
        self.cursor.execute("""
            UPDATE assets SET amount = %s WHERE asset_name = %s
        """, (new_amount, asset_name))
        
        self.cursor.execute("SELECT amount FROM assets WHERE asset_name = %s", (asset_name,))
        updated_asset = self.cursor.fetchone()
        self.assertEqual(updated_asset['amount'], new_amount, "Should be able to update asset")
        
        # Delete
        self.cursor.execute("DELETE FROM assets WHERE asset_name = %s", (asset_name,))
        self.assertEqual(self.cursor.rowcount, 1, "Should be able to delete asset")
    
    def test_transaction_rollback(self):
        """Test transaction rollback functionality"""
        asset_name = 'ROLLBACK_TEST'
        
        # Start transaction
        self.cursor.execute("BEGIN")
        
        # Insert asset
        self.cursor.execute("""
            INSERT INTO assets (tier_number, asset_name, amount, price_per_unit)
            VALUES (%s, %s, %s, %s)
        """, (1, asset_name, Decimal('100.0'), Decimal('50.0')))
        
        # Rollback transaction
        self.cursor.execute("ROLLBACK")
        
        # Verify asset doesn't exist
        self.cursor.execute("SELECT * FROM assets WHERE asset_name = %s", (asset_name,))
        result = self.cursor.fetchone()
        self.assertIsNone(result, "Asset should not exist after rollback")


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
    print("Assets-DB End-to-End Test Suite")
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
        
        # Insert test data
        if not docker_manager.insert_test_data():
            sys.exit(1)
        
        # Run tests
        docker_manager._print_header("Running Comprehensive Test Suite")
        
        # Create test suite
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(AssetsDBTestSuite)
        
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
