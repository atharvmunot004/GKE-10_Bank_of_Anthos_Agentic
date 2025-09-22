import os
import logging
import psycopg2
import random
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
import yfinance as yf
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
ASSETS_DB_URI = os.environ.get('ASSETS_DB_URI', 'postgresql://assets-admin:assets-pwd@assets-db:5432/assets-db')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(ASSETS_DB_URI)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def get_assets_by_tier(tier_number):
    """Get all assets for a specific tier from assets-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT asset_id, tier_number, asset_name, amount, price_per_unit, last_updated
            FROM assets 
            WHERE tier_number = %s
        """, (tier_number,))
        
        assets = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return assets
        
    except Exception as e:
        logger.error(f"Failed to get assets by tier: {e}")
        raise

def simulate_crypto_price(current_price, volatility=0.05):
    """Simulate cryptocurrency price movement."""
    # Crypto has higher volatility
    change_percent = random.uniform(-volatility, volatility)
    new_price = current_price * (1 + change_percent)
    return round(new_price, 2)

def simulate_etf_price(current_price, volatility=0.02):
    """Simulate ETF price movement."""
    # ETFs have moderate volatility
    change_percent = random.uniform(-volatility, volatility)
    new_price = current_price * (1 + change_percent)
    return round(new_price, 2)

def simulate_mutual_fund_price(current_price, volatility=0.015):
    """Simulate mutual fund price movement."""
    # Mutual funds have lower volatility
    change_percent = random.uniform(-volatility, volatility)
    new_price = current_price * (1 + change_percent)
    return round(new_price, 2)

def simulate_equity_price(current_price, volatility=0.03):
    """Simulate equity price movement."""
    # Equities have moderate volatility
    change_percent = random.uniform(-volatility, volatility)
    new_price = current_price * (1 + change_percent)
    return round(new_price, 2)

def get_real_market_data(symbol, asset_type):
    """Get real market data for a symbol if possible."""
    try:
        if asset_type == "CRYPTO":
            # For crypto, we'll use simulation as real API might be complex
            return None
        elif asset_type in ["ETF", "MUTUAL-FUND", "EQUITY"]:
            # Try to get real data from yfinance
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if not hist.empty:
                latest_price = hist['Close'].iloc[-1]
                return float(latest_price)
    except Exception as e:
        logger.warning(f"Failed to get real market data for {symbol}: {e}")
    
    return None

def update_asset_price(asset_id, new_price):
    """Update asset price in assets-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE assets 
            SET price_per_unit = %s, last_updated = CURRENT_TIMESTAMP
            WHERE asset_id = %s
        """, (new_price, asset_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated asset {asset_id} price to {new_price}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update asset price: {e}")
        raise

def generate_market_analytics(assets, asset_type):
    """Generate market analytics for AI agent consumption."""
    analytics = {
        "market_type": asset_type,
        "timestamp": datetime.now().isoformat(),
        "total_assets": len(assets),
        "price_summary": {
            "min_price": min(asset['price_per_unit'] for asset in assets),
            "max_price": max(asset['price_per_unit'] for asset in assets),
            "avg_price": sum(asset['price_per_unit'] for asset in assets) / len(assets),
            "total_market_value": sum(asset['amount'] * asset['price_per_unit'] for asset in assets)
        },
        "volatility_analysis": {
            "high_volatility_assets": [],
            "stable_assets": [],
            "recommended_for_short_term": [],
            "recommended_for_long_term": []
        },
        "portfolio_recommendations": {
            "diversification_score": 0.0,
            "risk_level": "medium",
            "suggested_allocation": {}
        }
    }
    
    # Analyze volatility based on asset type
    for asset in assets:
        asset_value = asset['amount'] * asset['price_per_unit']
        
        if asset_type == "CRYPTO":
            analytics["volatility_analysis"]["high_volatility_assets"].append({
                "name": asset['asset_name'],
                "price": asset['price_per_unit'],
                "value": asset_value,
                "risk": "high"
            })
            analytics["portfolio_recommendations"]["suggested_allocation"][asset['asset_name']] = "5-15%"
            
        elif asset_type == "ETF":
            if asset['price_per_unit'] > 1000:
                analytics["volatility_analysis"]["stable_assets"].append({
                    "name": asset['asset_name'],
                    "price": asset['price_per_unit'],
                    "value": asset_value,
                    "risk": "low"
                })
                analytics["portfolio_recommendations"]["suggested_allocation"][asset['asset_name']] = "20-40%"
            else:
                analytics["volatility_analysis"]["recommended_for_long_term"].append({
                    "name": asset['asset_name'],
                    "price": asset['price_per_unit'],
                    "value": asset_value,
                    "risk": "medium"
                })
                analytics["portfolio_recommendations"]["suggested_allocation"][asset['asset_name']] = "15-30%"
                
        elif asset_type == "MUTUAL-FUND":
            analytics["volatility_analysis"]["recommended_for_long_term"].append({
                "name": asset['asset_name'],
                "price": asset['price_per_unit'],
                "value": asset_value,
                "risk": "low"
            })
            analytics["portfolio_recommendations"]["suggested_allocation"][asset['asset_name']] = "10-25%"
            
        elif asset_type == "EQUITY":
            if asset['price_per_unit'] > 500:
                analytics["volatility_analysis"]["recommended_for_short_term"].append({
                    "name": asset['asset_name'],
                    "price": asset['price_per_unit'],
                    "value": asset_value,
                    "risk": "medium-high"
                })
                analytics["portfolio_recommendations"]["suggested_allocation"][asset['asset_name']] = "10-20%"
            else:
                analytics["volatility_analysis"]["stable_assets"].append({
                    "name": asset['asset_name'],
                    "price": asset['price_per_unit'],
                    "value": asset_value,
                    "risk": "medium"
                })
                analytics["portfolio_recommendations"]["suggested_allocation"][asset['asset_name']] = "15-30%"
    
    # Calculate diversification score
    if len(assets) >= 3:
        analytics["portfolio_recommendations"]["diversification_score"] = 0.8
    elif len(assets) >= 2:
        analytics["portfolio_recommendations"]["diversification_score"] = 0.6
    else:
        analytics["portfolio_recommendations"]["diversification_score"] = 0.3
    
    # Set risk level based on asset type
    if asset_type == "CRYPTO":
        analytics["portfolio_recommendations"]["risk_level"] = "high"
    elif asset_type in ["ETF", "EQUITY"]:
        analytics["portfolio_recommendations"]["risk_level"] = "medium"
    else:
        analytics["portfolio_recommendations"]["risk_level"] = "low"
    
    return analytics

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

@app.route('/api/v1/market-data', methods=['POST'])
def get_market_data():
    """
    Get market data for specified asset type.
    
    Request Body:
        {
            "type": "CRYPTO" | "ETF" | "MUTUAL-FUND" | "EQUITY"
        }
    
    Returns:
        JSON response with market data and analytics
    """
    try:
        data = request.get_json()
        asset_type = data.get('type')
        
        if not asset_type or asset_type not in ['CRYPTO', 'ETF', 'MUTUAL-FUND', 'EQUITY']:
            return jsonify({
                "status": "failed",
                "error": "Invalid asset type",
                "message": "Type must be one of: CRYPTO, ETF, MUTUAL-FUND, EQUITY"
            }), 400
        
        logger.info(f"Processing market data request for type: {asset_type}")
        
        # Map asset types to tier numbers
        tier_mapping = {
            'CRYPTO': 1,
            'ETF': 2,
            'MUTUAL-FUND': 2,
            'EQUITY': 2
        }
        
        tier_number = tier_mapping[asset_type]
        
        # Get assets for this tier
        assets = get_assets_by_tier(tier_number)
        
        if not assets:
            return jsonify({
                "status": "failed",
                "error": "No assets found",
                "message": f"No assets found for type {asset_type}"
            }), 404
        
        logger.info(f"Found {len(assets)} assets for type {asset_type}")
        
        # Update prices with market simulation
        updated_assets = []
        for asset in assets:
            current_price = float(asset['price_per_unit'])
            
            # Try to get real market data first
            real_price = get_real_market_data(asset['asset_name'], asset_type)
            
            if real_price:
                new_price = real_price
                logger.info(f"Using real market data for {asset['asset_name']}: {new_price}")
            else:
                # Use simulation based on asset type
                if asset_type == 'CRYPTO':
                    new_price = simulate_crypto_price(current_price)
                elif asset_type == 'ETF':
                    new_price = simulate_etf_price(current_price)
                elif asset_type == 'MUTUAL-FUND':
                    new_price = simulate_mutual_fund_price(current_price)
                elif asset_type == 'EQUITY':
                    new_price = simulate_equity_price(current_price)
                
                logger.info(f"Simulated price for {asset['asset_name']}: {current_price} -> {new_price}")
            
            # Update database with new price
            update_asset_price(asset['asset_id'], new_price)
            
            # Update asset data
            asset['price_per_unit'] = new_price
            asset['market_value'] = asset['amount'] * new_price
            asset['price_change'] = ((new_price - current_price) / current_price) * 100
            updated_assets.append(asset)
        
        # Generate market analytics
        analytics = generate_market_analytics(updated_assets, asset_type)
        
        logger.info(f"Successfully processed market data for {asset_type}")
        
        return jsonify({
            "status": "success",
            "asset_type": asset_type,
            "timestamp": datetime.now().isoformat(),
            "assets": [
                {
                    "asset_id": asset['asset_id'],
                    "asset_name": asset['asset_name'],
                    "tier_number": asset['tier_number'],
                    "amount": float(asset['amount']),
                    "price_per_unit": asset['price_per_unit'],
                    "market_value": asset['market_value'],
                    "price_change_percent": round(asset['price_change'], 2),
                    "last_updated": asset['last_updated'].isoformat()
                } for asset in updated_assets
            ],
            "analytics": analytics,
            "message": f"Market data updated successfully for {asset_type} assets"
        }), 200
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return jsonify({
            "status": "failed",
            "error": "Invalid input data"
        }), 400
    except Exception as e:
        logger.error(f"Error processing market data: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

@app.route('/api/v1/market-summary', methods=['GET'])
def get_market_summary():
    """Get overall market summary across all asset types."""
    try:
        all_assets = []
        for tier in [1, 2, 3]:
            assets = get_assets_by_tier(tier)
            all_assets.extend(assets)
        
        if not all_assets:
            return jsonify({
                "status": "failed",
                "error": "No assets found"
            }), 404
        
        # Calculate overall market metrics
        total_market_value = sum(asset['amount'] * asset['price_per_unit'] for asset in all_assets)
        
        tier_summary = {}
        for tier in [1, 2, 3]:
            tier_assets = [asset for asset in all_assets if asset['tier_number'] == tier]
            if tier_assets:
                tier_value = sum(asset['amount'] * asset['price_per_unit'] for asset in tier_assets)
                tier_summary[f"tier_{tier}"] = {
                    "asset_count": len(tier_assets),
                    "total_value": tier_value,
                    "percentage": (tier_value / total_market_value) * 100
                }
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_assets": len(all_assets),
            "total_market_value": total_market_value,
            "tier_breakdown": tier_summary,
            "market_health": "stable" if len(all_assets) >= 3 else "limited"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting market summary: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Market Reader Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
