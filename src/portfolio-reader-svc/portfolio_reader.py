import os
import json
import logging
import psycopg2
from datetime import datetime
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database connection
USER_PORTFOLIO_DB_URI = os.environ.get('USER_PORTFOLIO_DB_URI', 'postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db')

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(USER_PORTFOLIO_DB_URI)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

@app.route('/ready', methods=['GET'])
def readiness():
    """Readiness check endpoint."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 500

@app.route('/api/v1/portfolio/<string:user_id>', methods=['GET'])
def get_portfolio(user_id):
    """Get user portfolio information."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get portfolio information
        cursor.execute("""
            SELECT accountid, currency, tier1_allocation, tier2_allocation, tier3_allocation, 
                   total_allocation, tier1_value, tier2_value, tier3_value, total_value,
                   created_at, updated_at
            FROM user_portfolios 
            WHERE accountid = %s
        """, (user_id,))
        
        portfolio = cursor.fetchone()
        
        if not portfolio:
            cursor.close()
            conn.close()
            return jsonify({"error": "Portfolio not found"}), 404
        
        # Get recent transactions
        cursor.execute("""
            SELECT id, transaction_type, tier1_change, tier2_change, tier3_change,
                   total_amount, fees, status, created_at, updated_at
            FROM portfolio_transactions 
            WHERE accountid = %s 
            ORDER BY created_at DESC 
            LIMIT 10
        """, (user_id,))
        
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert portfolio to serializable format
        portfolio_data = {
            "accountid": portfolio['accountid'],
            "currency": portfolio['currency'],
            "tier1_allocation": float(portfolio['tier1_allocation']),
            "tier2_allocation": float(portfolio['tier2_allocation']),
            "tier3_allocation": float(portfolio['tier3_allocation']),
            "total_allocation": float(portfolio['total_allocation']),
            "tier1_value": float(portfolio['tier1_value']),
            "tier2_value": float(portfolio['tier2_value']),
            "tier3_value": float(portfolio['tier3_value']),
            "total_value": float(portfolio['total_value']),
            "created_at": portfolio['created_at'].isoformat(),
            "updated_at": portfolio['updated_at'].isoformat()
        }
        
        # Convert transactions to serializable format
        transaction_list = []
        for tx in transactions:
            transaction_list.append({
                "id": str(tx['id']),
                "transaction_type": tx['transaction_type'],
                "tier1_change": float(tx['tier1_change']),
                "tier2_change": float(tx['tier2_change']),
                "tier3_change": float(tx['tier3_change']),
                "total_amount": float(tx['total_amount']),
                "fees": float(tx['fees']),
                "status": tx['status'],
                "created_at": tx['created_at'].isoformat(),
                "updated_at": tx['updated_at'].isoformat()
            })
        
        response_data = {
            "portfolio": portfolio_data,
            "transactions": transaction_list
        }
        
        logger.info(f"Successfully retrieved portfolio for user {user_id}")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/portfolio/<string:user_id>/transactions', methods=['GET'])
def get_portfolio_transactions(user_id):
    """Get portfolio transactions for a user."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if portfolio exists
        cursor.execute("SELECT accountid FROM user_portfolios WHERE accountid = %s", (user_id,))
        portfolio = cursor.fetchone()
        
        if not portfolio:
            cursor.close()
            conn.close()
            return jsonify({"error": "Portfolio not found"}), 404
        
        # Get transactions with pagination
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        cursor.execute("""
            SELECT id, transaction_type, tier1_change, tier2_change, tier3_change,
                   total_amount, fees, status, created_at, updated_at
            FROM portfolio_transactions 
            WHERE accountid = %s 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """, (user_id, limit, offset))
        
        transactions = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert to serializable format
        transaction_list = []
        for tx in transactions:
            transaction_list.append({
                "id": str(tx['id']),
                "transaction_type": tx['transaction_type'],
                "tier1_change": float(tx['tier1_change']),
                "tier2_change": float(tx['tier2_change']),
                "tier3_change": float(tx['tier3_change']),
                "total_amount": float(tx['total_amount']),
                "fees": float(tx['fees']),
                "status": tx['status'],
                "created_at": tx['created_at'].isoformat(),
                "updated_at": tx['updated_at'].isoformat()
            })
        
        logger.info(f"Successfully retrieved {len(transaction_list)} transactions for user {user_id}")
        return jsonify(transaction_list), 200
        
    except Exception as e:
        logger.error(f"Failed to get portfolio transactions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/portfolio/<string:user_id>/summary', methods=['GET'])
def get_portfolio_summary(user_id):
    """Get portfolio summary with analytics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get portfolio information
        cursor.execute("""
            SELECT accountid, currency, tier1_allocation, tier2_allocation, tier3_allocation, 
                   total_allocation, tier1_value, tier2_value, tier3_value, total_value,
                   created_at, updated_at
            FROM user_portfolios 
            WHERE accountid = %s
        """, (user_id,))
        
        portfolio = cursor.fetchone()
        
        if not portfolio:
            cursor.close()
            conn.close()
            return jsonify({"error": "Portfolio not found"}), 404
        
        # Calculate basic analytics
        total_value = float(portfolio['total_value'])
        total_invested = 0
        total_gain_loss = 0
        
        # Get total invested from completed transactions
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) as total_invested
            FROM portfolio_transactions 
            WHERE accountid = %s AND transaction_type = 'INVEST' AND status = 'COMPLETED'
        """, (user_id,))
        
        invested_result = cursor.fetchone()
        if invested_result:
            total_invested = float(invested_result['total_invested'])
        
        # Calculate gain/loss
        total_gain_loss = total_value - total_invested
        gain_loss_percentage = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
        
        # Get transaction counts
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                COUNT(CASE WHEN transaction_type = 'INVEST' THEN 1 END) as invest_count,
                COUNT(CASE WHEN transaction_type = 'WITHDRAWAL' THEN 1 END) as withdrawal_count,
                COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_count
            FROM portfolio_transactions 
            WHERE accountid = %s
        """, (user_id,))
        
        stats_result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Build summary response
        summary = {
            "accountid": portfolio['accountid'],
            "currency": portfolio['currency'],
            "current_value": {
                "total_value": total_value,
                "tier1_value": float(portfolio['tier1_value']),
                "tier2_value": float(portfolio['tier2_value']),
                "tier3_value": float(portfolio['tier3_value'])
            },
            "allocation": {
                "tier1_allocation": float(portfolio['tier1_allocation']),
                "tier2_allocation": float(portfolio['tier2_allocation']),
                "tier3_allocation": float(portfolio['tier3_allocation']),
                "total_allocation": float(portfolio['total_allocation'])
            },
            "analytics": {
                "total_invested": total_invested,
                "total_gain_loss": total_gain_loss,
                "gain_loss_percentage": round(gain_loss_percentage, 2),
                "total_transactions": stats_result['total_transactions'],
                "invest_count": stats_result['invest_count'],
                "withdrawal_count": stats_result['withdrawal_count'],
                "completed_count": stats_result['completed_count']
            },
            "timestamps": {
                "created_at": portfolio['created_at'].isoformat(),
                "updated_at": portfolio['updated_at'].isoformat()
            }
        }
        
        logger.info(f"Successfully retrieved portfolio summary for user {user_id}")
        return jsonify(summary), 200
        
    except Exception as e:
        logger.error(f"Failed to get portfolio summary: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 8080))
