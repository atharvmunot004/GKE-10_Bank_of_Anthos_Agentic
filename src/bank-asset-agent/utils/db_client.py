#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Database Client Utilities

import psycopg2
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class AssetsDatabaseClient:
    """Database client for assets-db"""
    
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string or os.environ.get('ASSETS_DB_URI')
        if not self.connection_string:
            raise ValueError("Assets database connection string not provided")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = psycopg2.connect(self.connection_string)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise Exception(f"Database connection failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def get_asset_info(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get asset information by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated 
                    FROM assets 
                    WHERE asset_id = %s
                """, (asset_id,))
                
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    return {
                        'asset_id': result[0],
                        'tier_number': result[1],
                        'asset_name': result[2],
                        'amount': result[3],
                        'price_per_unit': result[4],
                        'last_updated': result[5]
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get asset info: {e}")
            raise Exception(f"Asset info retrieval failed: {e}")
    
    def get_assets_by_tier(self, tier_number: int) -> List[Dict[str, Any]]:
        """Get all assets by tier number"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated 
                    FROM assets 
                    WHERE tier_number = %s
                    ORDER BY asset_name
                """, (tier_number,))
                
                results = cursor.fetchall()
                cursor.close()
                
                return [
                    {
                        'asset_id': row[0],
                        'tier_number': row[1],
                        'asset_name': row[2],
                        'amount': row[3],
                        'price_per_unit': row[4],
                        'last_updated': row[5]
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Failed to get assets by tier: {e}")
            raise Exception(f"Assets by tier retrieval failed: {e}")
    
    def get_all_assets(self) -> List[Dict[str, Any]]:
        """Get all assets"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated 
                    FROM assets 
                    ORDER BY tier_number, asset_name
                """)
                
                results = cursor.fetchall()
                cursor.close()
                
                return [
                    {
                        'asset_id': row[0],
                        'tier_number': row[1],
                        'asset_name': row[2],
                        'amount': row[3],
                        'price_per_unit': row[4],
                        'last_updated': row[5]
                    }
                    for row in results
                ]
        except Exception as e:
            logger.error(f"Failed to get all assets: {e}")
            raise Exception(f"All assets retrieval failed: {e}")
    
    def update_asset_price(self, asset_id: str, new_price: float) -> bool:
        """Update asset price"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE assets 
                    SET price_per_unit = %s, last_updated = CURRENT_TIMESTAMP 
                    WHERE asset_id = %s
                """, (new_price, asset_id))
                
                rows_affected = cursor.rowcount
                conn.commit()
                cursor.close()
                
                return rows_affected > 0
        except Exception as e:
            logger.error(f"Failed to update asset price: {e}")
            raise Exception(f"Asset price update failed: {e}")
    
    def update_asset_availability(self, asset_id: str, amount: float) -> bool:
        """Update asset availability amount"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE assets 
                    SET amount = %s, last_updated = CURRENT_TIMESTAMP 
                    WHERE asset_id = %s
                """, (amount, asset_id))
                
                rows_affected = cursor.rowcount
                conn.commit()
                cursor.close()
                
                return rows_affected > 0
        except Exception as e:
            logger.error(f"Failed to update asset availability: {e}")
            raise Exception(f"Asset availability update failed: {e}")
    
    def add_asset(self, asset_data: Dict[str, Any]) -> str:
        """Add new asset"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO assets (tier_number, asset_name, amount, price_per_unit, last_updated)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING asset_id
                """, (
                    asset_data['tier_number'],
                    asset_data['asset_name'],
                    asset_data['amount'],
                    asset_data['price_per_unit']
                ))
                
                asset_id = cursor.fetchone()[0]
                conn.commit()
                cursor.close()
                
                return asset_id
        except Exception as e:
            logger.error(f"Failed to add asset: {e}")
            raise Exception(f"Asset addition failed: {e}")
    
    def check_asset_availability(self, asset_id: str, requested_amount: float) -> bool:
        """Check if asset has sufficient availability"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT amount FROM assets WHERE asset_id = %s
                """, (asset_id,))
                
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    available_amount = result[0]
                    return available_amount >= requested_amount
                return False
        except Exception as e:
            logger.error(f"Failed to check asset availability: {e}")
            raise Exception(f"Asset availability check failed: {e}")
    
    def get_asset_statistics(self) -> Dict[str, Any]:
        """Get asset statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get total assets by tier
                cursor.execute("""
                    SELECT tier_number, COUNT(*) as count, SUM(amount) as total_amount, AVG(price_per_unit) as avg_price
                    FROM assets 
                    GROUP BY tier_number
                    ORDER BY tier_number
                """)
                
                tier_stats = cursor.fetchall()
                
                # Get overall statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_assets,
                        SUM(amount) as total_amount,
                        AVG(price_per_unit) as avg_price,
                        MIN(price_per_unit) as min_price,
                        MAX(price_per_unit) as max_price
                    FROM assets
                """)
                
                overall_stats = cursor.fetchone()
                cursor.close()
                
                return {
                    'tier_statistics': [
                        {
                            'tier_number': row[0],
                            'count': row[1],
                            'total_amount': row[2],
                            'avg_price': row[3]
                        }
                        for row in tier_stats
                    ],
                    'overall_statistics': {
                        'total_assets': overall_stats[0],
                        'total_amount': overall_stats[1],
                        'avg_price': overall_stats[2],
                        'min_price': overall_stats[3],
                        'max_price': overall_stats[4]
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get asset statistics: {e}")
            raise Exception(f"Asset statistics retrieval failed: {e}")

def create_database_client(db_type: str, connection_string: str = None):
    """Factory function to create database clients"""
    clients = {
        'assets': AssetsDatabaseClient
    }
    
    client_class = clients.get(db_type)
    if not client_class:
        raise ValueError(f"Unknown database type: {db_type}")
    
    return client_class(connection_string)
