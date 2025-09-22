import os
import logging
import psycopg2
import random
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
ASSETS_DB_URI = os.environ.get('ASSETS_DB_URI', 'postgresql://assets-admin:assets-pwd@assets-db:5432/assets-db')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))

# Tier pool environment variables (current available funds)
TIER1_POOL = float(os.environ.get('TIER1', '1000000.0'))  # Default 1M for tier 1
TIER2_POOL = float(os.environ.get('TIER2', '2000000.0'))  # Default 2M for tier 2
TIER3_POOL = float(os.environ.get('TIER3', '500000.0'))   # Default 500K for tier 3

# Tier market value environment variables (calculated from assets-db)
TIER1_MV = float(os.environ.get('TIER1_MV', '0.0'))
TIER2_MV = float(os.environ.get('TIER2_MV', '0.0'))
TIER3_MV = float(os.environ.get('TIER3_MV', '0.0'))

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(ASSETS_DB_URI)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def update_tier_market_values():
    """Update tier market value environment variables from assets-db."""
    global TIER1_MV, TIER2_MV, TIER3_MV
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Calculate market values for each tier
        for tier in [1, 2, 3]:
            cursor.execute("""
                SELECT COALESCE(SUM(amount * price_per_unit), 0) as market_value
                FROM assets 
                WHERE tier_number = %s
            """, (tier,))
            
            result = cursor.fetchone()
            market_value = float(result[0]) if result else 0.0
            
            if tier == 1:
                TIER1_MV = market_value
            elif tier == 2:
                TIER2_MV = market_value
            elif tier == 3:
                TIER3_MV = market_value
            
            logger.info(f"Updated TIER{tier}_MV: {market_value}")
        
        cursor.close()
        conn.close()
        
        # Update environment variables
        os.environ['TIER1_MV'] = str(TIER1_MV)
        os.environ['TIER2_MV'] = str(TIER2_MV)
        os.environ['TIER3_MV'] = str(TIER3_MV)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update tier market values: {e}")
        return False

def get_asset_by_id(asset_id):
    """Get asset by ID from assets-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated
            FROM assets 
            WHERE asset_id = %s
        """, (asset_id,))
        
        asset = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return dict(asset) if asset else None
        
    except Exception as e:
        logger.error(f"Failed to get asset by ID: {e}")
        return None

def create_asset(asset_id, asset_type, tier_number, asset_name, amount, price):
    """Create new asset in assets-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO assets (asset_id, tier_number, asset_name, amount, price_per_unit, last_updated)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (asset_id, tier_number, asset_name, amount, price))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Created new asset: {asset_name} (ID: {asset_id})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create asset: {e}")
        return False

def update_asset_amount(asset_id, new_amount):
    """Update asset amount in assets-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE assets 
            SET amount = %s, last_updated = CURRENT_TIMESTAMP
            WHERE asset_id = %s
        """, (new_amount, asset_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated asset {asset_id} amount to {new_amount}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update asset amount: {e}")
        return False

def get_tier_pool(tier_number):
    """Get available pool amount for tier."""
    if tier_number == 1:
        return TIER1_POOL
    elif tier_number == 2:
        return TIER2_POOL
    elif tier_number == 3:
        return TIER3_POOL
    else:
        return 0.0

def calculate_order_probability(request_price, request_amount, market_price, market_amount):
    """Calculate realistic probability of order execution based on price and volume."""
    try:
        # Price difference factor
        price_diff = abs(request_price - market_price) / market_price
        price_factor = max(0.1, 1.0 - (price_diff * 2))  # Higher price diff = lower probability
        
        # Volume factor
        volume_ratio = min(request_amount, market_amount) / max(request_amount, market_amount)
        volume_factor = max(0.2, volume_ratio)  # Higher volume ratio = higher probability
        
        # Market liquidity factor (simulate market conditions)
        liquidity_factor = random.uniform(0.7, 1.0)
        
        # Combined probability
        probability = price_factor * volume_factor * liquidity_factor
        
        # Add some randomness for realistic market behavior
        probability = min(0.95, max(0.05, probability))
        
        logger.info(f"Order probability calculation: price_factor={price_factor:.2f}, "
                   f"volume_factor={volume_factor:.2f}, liquidity_factor={liquidity_factor:.2f}, "
                   f"final_probability={probability:.2f}")
        
        return probability
        
    except Exception as e:
        logger.error(f"Error calculating order probability: {e}")
        return 0.5  # Default 50% probability

def process_buy_order(asset_id, asset_type, tier_number, asset_name, amount_trade, price):
    """Process BUY order."""
    try:
        # Check if we have sufficient funds in the tier pool
        required_amount = amount_trade * price
        available_pool = get_tier_pool(tier_number)
        
        if required_amount > available_pool:
            return {
                "status": "failed",
                "error": "insufficient_funds",
                "message": f"Insufficient funds in tier {tier_number} pool. Required: {required_amount}, Available: {available_pool}",
                "required_amount": required_amount,
                "available_amount": available_pool
            }
        
        # Get existing asset or prepare for creation
        existing_asset = get_asset_by_id(asset_id)
        
        if existing_asset:
            # Asset exists, calculate execution probability
            market_price = existing_asset['price_per_unit']
            market_amount = existing_asset['amount']
            execution_probability = calculate_order_probability(price, amount_trade, market_price, market_amount)
            
            # Determine if order executes based on probability
            if random.random() <= execution_probability:
                # Order executed - update asset amount
                new_amount = existing_asset['amount'] + amount_trade
                if update_asset_amount(asset_id, new_amount):
                    return {
                        "status": "executed",
                        "order_id": str(uuid.uuid4()),
                        "asset_id": asset_id,
                        "asset_name": asset_name,
                        "amount_traded": amount_trade,
                        "price_executed": price,
                        "total_value": amount_trade * price,
                        "new_amount": new_amount,
                        "execution_probability": execution_probability,
                        "message": "BUY order executed successfully"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "database_error",
                        "message": "Failed to update asset in database"
                    }
            else:
                return {
                    "status": "failed",
                    "error": "order_rejected",
                    "message": f"Order rejected due to market conditions. Execution probability: {execution_probability:.2f}",
                    "execution_probability": execution_probability
                }
        else:
            # Asset doesn't exist, create new asset
            execution_probability = calculate_order_probability(price, amount_trade, price, amount_trade)
            
            if random.random() <= execution_probability:
                if create_asset(asset_id, asset_type, tier_number, asset_name, amount_trade, price):
                    return {
                        "status": "executed",
                        "order_id": str(uuid.uuid4()),
                        "asset_id": asset_id,
                        "asset_name": asset_name,
                        "amount_traded": amount_trade,
                        "price_executed": price,
                        "total_value": amount_trade * price,
                        "new_amount": amount_trade,
                        "execution_probability": execution_probability,
                        "message": "BUY order executed successfully - new asset created"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "database_error",
                        "message": "Failed to create new asset in database"
                    }
            else:
                return {
                    "status": "failed",
                    "error": "order_rejected",
                    "message": f"Order rejected due to market conditions. Execution probability: {execution_probability:.2f}",
                    "execution_probability": execution_probability
                }
                
    except Exception as e:
        logger.error(f"Error processing BUY order: {e}")
        return {
            "status": "failed",
            "error": "processing_error",
            "message": str(e)
        }

def process_sell_order(asset_id, asset_type, tier_number, asset_name, amount_trade, price):
    """Process SELL order."""
    try:
        # Get existing asset
        existing_asset = get_asset_by_id(asset_id)
        
        if not existing_asset:
            return {
                "status": "failed",
                "error": "asset_not_found",
                "message": f"Asset with ID {asset_id} not found in database"
            }
        
        # Check if we have sufficient assets to sell
        available_amount = existing_asset['amount']
        required_value = amount_trade * price
        available_value = available_amount * existing_asset['price_per_unit']
        
        if required_value > available_value:
            return {
                "status": "failed",
                "error": "insufficient_assets",
                "message": f"Insufficient assets to sell. Required: {required_value}, Available: {available_value}",
                "required_value": required_value,
                "available_value": available_value
            }
        
        # Calculate execution probability
        market_price = existing_asset['price_per_unit']
        market_amount = existing_asset['amount']
        execution_probability = calculate_order_probability(price, amount_trade, market_price, market_amount)
        
        # Determine if order executes based on probability
        if random.random() <= execution_probability:
            # Order executed - update asset amount
            new_amount = existing_asset['amount'] - amount_trade
            
            if new_amount < 0:
                return {
                    "status": "failed",
                    "error": "insufficient_assets",
                    "message": f"Cannot sell {amount_trade} units, only {existing_asset['amount']} available"
                }
            
            if update_asset_amount(asset_id, new_amount):
                return {
                    "status": "executed",
                    "order_id": str(uuid.uuid4()),
                    "asset_id": asset_id,
                    "asset_name": asset_name,
                    "amount_traded": amount_trade,
                    "price_executed": price,
                    "total_value": amount_trade * price,
                    "new_amount": new_amount,
                    "execution_probability": execution_probability,
                    "message": "SELL order executed successfully"
                }
            else:
                return {
                    "status": "failed",
                    "error": "database_error",
                    "message": "Failed to update asset in database"
                }
        else:
            return {
                "status": "failed",
                "error": "order_rejected",
                "message": f"Order rejected due to market conditions. Execution probability: {execution_probability:.2f}",
                "execution_probability": execution_probability
            }
                
    except Exception as e:
        logger.error(f"Error processing SELL order: {e}")
        return {
            "status": "failed",
            "error": "processing_error",
            "message": str(e)
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check database connectivity
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        return jsonify({"status": "ready"}), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 500

@app.route('/api/v1/execute-order', methods=['POST'])
def execute_order():
    """
    Execute buy or sell order for assets.
    
    Request Body:
        {
            "asset_id": "string",
            "asset_type": "string",
            "tier_number": 1|2|3,
            "asset_name": "string",
            "amount_trade": float,
            "price": float,
            "purpose": "BUY"|"SELL"
        }
    
    Returns:
        JSON response with order execution result
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['asset_id', 'asset_type', 'tier_number', 'asset_name', 'amount_trade', 'price', 'purpose']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "failed",
                    "error": "missing_field",
                    "message": f"Required field '{field}' is missing"
                }), 400
        
        # Validate field types and values
        asset_id = str(data['asset_id'])
        asset_type = str(data['asset_type'])
        tier_number = int(data['tier_number'])
        asset_name = str(data['asset_name'])
        amount_trade = float(data['amount_trade'])
        price = float(data['price'])
        purpose = str(data['purpose']).upper()
        
        if tier_number not in [1, 2, 3]:
            return jsonify({
                "status": "failed",
                "error": "invalid_tier",
                "message": "Tier number must be 1, 2, or 3"
            }), 400
        
        if purpose not in ['BUY', 'SELL']:
            return jsonify({
                "status": "failed",
                "error": "invalid_purpose",
                "message": "Purpose must be 'BUY' or 'SELL'"
            }), 400
        
        if amount_trade <= 0 or price <= 0:
            return jsonify({
                "status": "failed",
                "error": "invalid_amount_or_price",
                "message": "Amount and price must be positive values"
            }), 400
        
        logger.info(f"Processing {purpose} order: {asset_name} (ID: {asset_id}), "
                   f"Amount: {amount_trade}, Price: {price}, Tier: {tier_number}")
        
        # Update tier market values before processing
        update_tier_market_values()
        
        # Process order based on purpose
        if purpose == 'BUY':
            result = process_buy_order(asset_id, asset_type, tier_number, asset_name, amount_trade, price)
        else:  # SELL
            result = process_sell_order(asset_id, asset_type, tier_number, asset_name, amount_trade, price)
        
        # Add metadata to response
        result['timestamp'] = datetime.now().isoformat()
        result['tier_number'] = tier_number
        result['asset_type'] = asset_type
        
        # Update tier market values after processing
        if result['status'] == 'executed':
            update_tier_market_values()
            result['updated_tier_values'] = {
                'TIER1_MV': TIER1_MV,
                'TIER2_MV': TIER2_MV,
                'TIER3_MV': TIER3_MV
            }
        
        return jsonify(result), 200 if result['status'] == 'executed' else 400
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return jsonify({
            "status": "failed",
            "error": "invalid_input",
            "message": str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error processing order: {e}")
        return jsonify({
            "status": "failed",
            "error": "processing_error",
            "message": str(e)
        }), 500

@app.route('/api/v1/tier-status', methods=['GET'])
def get_tier_status():
    """Get current tier pool and market value status."""
    try:
        # Update tier market values
        update_tier_market_values()
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "tier_pools": {
                "TIER1": TIER1_POOL,
                "TIER2": TIER2_POOL,
                "TIER3": TIER3_POOL
            },
            "tier_market_values": {
                "TIER1_MV": TIER1_MV,
                "TIER2_MV": TIER2_MV,
                "TIER3_MV": TIER3_MV
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting tier status: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Execute Order Service on port {port}")
    
    # Initialize tier market values on startup
    update_tier_market_values()
    
    app.run(host='0.0.0.0', port=port, debug=False)
