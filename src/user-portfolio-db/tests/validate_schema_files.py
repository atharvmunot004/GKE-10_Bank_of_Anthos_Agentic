#!/usr/bin/env python3
"""
Schema File Validation Script for User Portfolio Database
This script validates the schema files without requiring a database connection.
"""

import os
import re
import sys
from pathlib import Path

def validate_schema_file(schema_file_path):
    """Validate the schema file structure and content."""
    print(f"🔍 Validating schema file: {schema_file_path}")
    
    if not os.path.exists(schema_file_path):
        print(f"❌ Schema file not found: {schema_file_path}")
        return False
    
    with open(schema_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    validation_results = {
        'extensions': False,
        'user_portfolios_table': False,
        'portfolio_transactions_table': False,
        'portfolio_analytics_table': False,
        'indexes': False,
        'views': False,
        'constraints': False
    }
    
    # Check for required extensions
    if 'CREATE EXTENSION' in content and 'uuid-ossp' in content:
        validation_results['extensions'] = True
        print("  ✅ Required extensions found")
    else:
        print("  ❌ Required extensions missing")
    
    # Check for user_portfolios table
    if 'CREATE TABLE' in content and 'user_portfolios' in content:
        if 'accountid VARCHAR(10)' in content:
            validation_results['user_portfolios_table'] = True
            print("  ✅ user_portfolios table with accountid found")
        else:
            print("  ❌ user_portfolios table missing accountid column")
    else:
        print("  ❌ user_portfolios table not found")
    
    # Check for portfolio_transactions table
    if 'CREATE TABLE' in content and 'portfolio_transactions' in content:
        if 'accountid VARCHAR(10)' in content and 'REFERENCES user_portfolios' in content:
            validation_results['portfolio_transactions_table'] = True
            print("  ✅ portfolio_transactions table with foreign key found")
        else:
            print("  ❌ portfolio_transactions table missing or invalid foreign key")
    else:
        print("  ❌ portfolio_transactions table not found")
    
    # Check for portfolio_analytics table
    if 'CREATE TABLE' in content and 'portfolio_analytics' in content:
        validation_results['portfolio_analytics_table'] = True
        print("  ✅ portfolio_analytics table found")
    else:
        print("  ❌ portfolio_analytics table not found")
    
    # Check for indexes
    if 'CREATE INDEX' in content and 'idx_user_portfolios_accountid' in content:
        validation_results['indexes'] = True
        print("  ✅ Required indexes found")
    else:
        print("  ❌ Required indexes missing")
    
    # Check for views
    if ('CREATE OR REPLACE VIEW' in content or 'CREATE VIEW' in content) and 'portfolio_summary' in content:
        validation_results['views'] = True
        print("  ✅ portfolio_summary view found")
    else:
        print("  ❌ portfolio_summary view not found")
    
    # Check for constraints
    if 'CONSTRAINT check_tier_allocation' in content and 'CONSTRAINT check_tier_value' in content:
        validation_results['constraints'] = True
        print("  ✅ Required constraints found")
    else:
        print("  ❌ Required constraints missing")
    
    return all(validation_results.values())

def validate_test_files():
    """Validate the test files structure."""
    print("\n🔍 Validating test files...")
    
    test_dir = Path(__file__).parent
    required_files = [
        'test_user_portfolio_db_updated.sql',
        'run_updated_tests.sh',
        'run_updated_tests.ps1',
        'TEST_VALIDATION_SUMMARY.md'
    ]
    
    all_files_exist = True
    for file_name in required_files:
        file_path = test_dir / file_name
        if file_path.exists():
            print(f"  ✅ {file_name} found")
        else:
            print(f"  ❌ {file_name} missing")
            all_files_exist = False
    
    return all_files_exist

def validate_column_types():
    """Validate specific column types in the schema."""
    print("\n🔍 Validating column data types...")
    
    schema_file = Path(__file__).parent.parent / 'initdb' / '0-user-portfolio-schema.sql'
    
    if not schema_file.exists():
        print(f"  ❌ Schema file not found: {schema_file}")
        return False
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_columns = {
        'accountid': 'VARCHAR(10)',
        'tier1_allocation': 'NUMERIC(15,2)',
        'tier2_allocation': 'NUMERIC(15,2)',
        'tier3_allocation': 'NUMERIC(15,2)',
        'total_allocation': 'NUMERIC(15,2)',
        'tier1_value': 'NUMERIC(15,2)',
        'tier2_value': 'NUMERIC(15,2)',
        'tier3_value': 'NUMERIC(15,2)',
        'total_value': 'NUMERIC(15,2)'
    }
    
    all_columns_valid = True
    for column_name, expected_type in required_columns.items():
        if f'{column_name} {expected_type}' in content:
            print(f"  ✅ {column_name} {expected_type} found")
        else:
            print(f"  ❌ {column_name} {expected_type} not found")
            all_columns_valid = False
    
    return all_columns_valid

def main():
    """Main validation function."""
    print("=" * 60)
    print("User Portfolio Database Schema Validation")
    print("=" * 60)
    
    # Get the directory of this script
    script_dir = Path(__file__).parent
    schema_file = script_dir.parent / 'initdb' / '0-user-portfolio-schema.sql'
    
    validation_results = []
    
    # Validate schema file
    schema_valid = validate_schema_file(schema_file)
    validation_results.append(("Schema File", schema_valid))
    
    # Validate column types
    columns_valid = validate_column_types()
    validation_results.append(("Column Types", columns_valid))
    
    # Validate test files
    test_files_valid = validate_test_files()
    validation_results.append(("Test Files", test_files_valid))
    
    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    
    all_valid = True
    for test_name, result in validation_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if not result:
            all_valid = False
    
    print("\n" + "=" * 60)
    if all_valid:
        print("🎉 All validations passed!")
        print("Database schema is ready for testing.")
        print("\nTo run the tests, you need:")
        print("1. PostgreSQL server running")
        print("2. psql client installed")
        print("3. Database creation privileges")
        print("\nThen run:")
        print("  ./run_updated_tests.sh")
        print("  or")
        print("  .\\run_updated_tests.ps1")
        return 0
    else:
        print("❌ Some validations failed.")
        print("Please fix the issues above before running database tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
