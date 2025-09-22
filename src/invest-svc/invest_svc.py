"""
Invest Service
Handles investment processing by integrating with user-tier-agent and updating user-portfolio-db.
"""

import os
import json
import uuid
import requests
import logging
import psycopg2
from datetime import datetime
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service endpoints
USER_TIER_AGENT_URI = os.environ.get('USER_TIER_AGENT_URI', 'http://user-tier-agent:8080')
USER_PORTFOLIO_DB_URI = os.environ.get('USER_PORTFOLIO_DB_URI', 'postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db')
BALANCE_READER_URI = os.environ.get('BALANCE_READER_URI', 'http://balancereader:8080')

# Request timeout
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))

def get_auth_headers_from_request(request) -> dict:
    """
    Extract JWT token from incoming request headers and prepare for external services.
    
    Args:
        request: Flask request object
        
    Returns:
        Dictionary containing Authorization header for external services
    """
    try:
        # Extract JWT token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.warning("No valid Authorization header found in request")
            return {
                'Content-Type': 'application/json'
            }
        
        # Extract token from "Bearer <token>" format
        token = auth_header.split(' ', 1)[1]
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    except Exception as e:
        logger.error(f"Failed to extract auth headers from request: {str(e)}")
        return {
            'Content-Type': 'application/json'
        }

def get_db_connection():
    """Get database connection."""
    try:
        return psycopg2.connect(USER_PORTFOLIO_DB_URI)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def check_account_balance(account_id: str, amount: float, auth_headers: dict) -> bool:
    """
    Check if account has sufficient balance for investment.
    
    Args:
        account_id: Account number to check
        amount: Investment amount
        auth_headers: Authentication headers for balancereader
        
    Returns:
        True if sufficient balance, False otherwise
    """
    try:
        logger.info(f"Checking balance for account {account_id}, amount: {amount}")
        
        response = requests.get(
            f'{BALANCE_READER_URI}/balances/{account_id}',
            headers=auth_headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            balance_data = response.json()
            current_balance = float(balance_data.get('balance', 0))
            
            logger.info(f"Account {account_id} balance: {current_balance}")
            return current_balance >= amount
        else:
            logger.error(f"Failed to get balance for account {account_id}: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking account balance: {e}")
        return False

def get_tier_allocation(account_id: str, amount: float, auth_headers: dict) -> dict:
    """
    Get tier allocation from user-tier-agent.
    
    Args:
        account_id: Account number
        amount: Investment amount
        auth_headers: Authentication headers
        
    Returns:
        Dictionary with tier allocation details
    """
    try:
        logger.info(f"Getting tier allocation for account {account_id}, amount: {amount}")
        
        # Generate UUID for this investment request
        investment_uuid = str(uuid.uuid4())
        
        tier_request = {
            "accountid": account_id,
            "amount": amount,
            "uuid": investment_uuid,
            "purpose": "INVEST"
        }
        
        response = requests.post(
            f'{USER_TIER_AGENT_URI}/allocate',
            json=tier_request,
            headers=auth_headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            tier_data = response.json()
            logger.info(f"Tier allocation received: {tier_data}")
            return tier_data
        else:
            logger.error(f"Failed to get tier allocation: {response.status_code}")
            raise Exception(f"Tier allocation failed: {response.text}")
            
    except Exception as e:
        logger.error(f"Error getting tier allocation: {e}")
        raise

def create_or_update_portfolio(account_id: str, tier_data: dict) -> str:
    """
    Create or update user portfolio with investment details.
    
    Args:
        account_id: Account number
        tier_data: Tier allocation data from user-tier-agent
        
    Returns:
        Portfolio ID
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if portfolio exists
        cursor.execute("""
            SELECT id, tier1_value, tier2_value, tier3_value, total_value
            FROM user_portfolios 
            WHERE user_id = %s
        """, (account_id,))
        
        portfolio = cursor.fetchone()
        
        if portfolio:
            # Update existing portfolio
            portfolio_id = str(portfolio['id'])
            new_tier1_value = float(portfolio['tier1_value']) + float(tier_data['tier1'])
            new_tier2_value = float(portfolio['tier2_value']) + float(tier_data['tier2'])
            new_tier3_value = float(portfolio['tier3_value']) + float(tier_data['tier3'])
            new_total_value = new_tier1_value + new_tier2_value + new_tier3_value
            
            # Calculate new allocation percentages
            new_tier1_allocation = (new_tier1_value / new_total_value) * 100 if new_total_value > 0 else 0
            new_tier2_allocation = (new_tier2_value / new_total_value) * 100 if new_total_value > 0 else 0
            new_tier3_allocation = (new_tier3_value / new_total_value) * 100 if new_total_value > 0 else 0
            
            cursor.execute("""
                UPDATE user_portfolios 
                SET 
                    tier1_value = %s,
                    tier2_value = %s,
                    tier3_value = %s,
                    total_value = %s,
                    tier1_allocation = %s,
                    tier2_allocation = %s,
                    tier3_allocation = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (new_tier1_value, new_tier2_value, new_tier3_value, new_total_value,
                  new_tier1_allocation, new_tier2_allocation, new_tier3_allocation, portfolio_id))
            
            logger.info(f"Updated existing portfolio {portfolio_id}")
            
        else:
            # Create new portfolio
            portfolio_id = str(uuid.uuid4())
            total_amount = float(tier_data['tier1']) + float(tier_data['tier2']) + float(tier_data['tier3'])
            
            # Calculate allocation percentages
            tier1_allocation = (float(tier_data['tier1']) / total_amount) * 100 if total_amount > 0 else 0
            tier2_allocation = (float(tier_data['tier2']) / total_amount) * 100 if total_amount > 0 else 0
            tier3_allocation = (float(tier_data['tier3']) / total_amount) * 100 if total_amount > 0 else 0
            
            cursor.execute("""
                INSERT INTO user_portfolios (
                    id, user_id, total_value, currency, tier1_allocation, tier2_allocation, tier3_allocation,
                    tier1_value, tier2_value, tier3_value, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """, (portfolio_id, account_id, total_amount, 'USD',
                  tier1_allocation, tier2_allocation, tier3_allocation,
                  tier_data['tier1'], tier_data['tier2'], tier_data['tier3']))
            
            logger.info(f"Created new portfolio {portfolio_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return portfolio_id
        
    except Exception as e:
        logger.error(f"Error creating/updating portfolio: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

def create_portfolio_transaction(portfolio_id: str, tier_data: dict) -> str:
    """
    Create portfolio transaction record.
    
    Args:
        portfolio_id: Portfolio ID
        tier_data: Tier allocation data
        
    Returns:
        Transaction ID
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        transaction_id = str(uuid.uuid4())
        total_amount = float(tier_data['tier1']) + float(tier_data['tier2']) + float(tier_data['tier3'])
        
        cursor.execute("""
            INSERT INTO portfolio_transactions (
                id, portfolio_id, transaction_type, tier1_change, tier2_change, tier3_change,
                total_amount, status, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """, (transaction_id, portfolio_id, 'DEPOSIT',
              tier_data['tier1'], tier_data['tier2'], tier_data['tier3'],
              total_amount, 'PENDING'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Created portfolio transaction {transaction_id}")
        return transaction_id
        
    except Exception as e:
        logger.error(f"Error creating portfolio transaction: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

@app.route('/ready', methods=['GET'])
def ready():
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
        return jsonify({"status": "not ready", "error": str(e)}), 503

@app.route('/api/v1/invest', methods=['POST'])
def invest():
    """Process investment request."""
    try:
        data = request.get_json()
        account_id = data.get('account_number')
        amount = float(data.get('amount', 0))
        
        if not account_id:
            return jsonify({"error": "Account number is required"}), 400
        
        if amount <= 0:
            return jsonify({"error": "Investment amount must be greater than 0"}), 400
        
        logger.info(f"Processing investment for account {account_id}, amount: {amount}")
        
        # Get authentication headers
        auth_headers = get_auth_headers_from_request(request)
        
        # Check account balance
        if not check_account_balance(account_id, amount, auth_headers):
            return jsonify({"error": "Insufficient balance for investment"}), 400
        
        # Get tier allocation
        tier_data = get_tier_allocation(account_id, amount, auth_headers)
        
        # Create or update portfolio
        portfolio_id = create_or_update_portfolio(account_id, tier_data)
        
        # Create portfolio transaction
        transaction_id = create_portfolio_transaction(portfolio_id, tier_data)
        
        logger.info(f"Investment processed successfully for account {account_id}")
        
        return jsonify({
            "status": "done",
            "portfolio_id": portfolio_id,
            "transaction_id": transaction_id,
            "total_invested": amount,
            "tier1_amount": float(tier_data['tier1']),
            "tier2_amount": float(tier_data['tier2']),
            "tier3_amount": float(tier_data['tier3']),
            "message": "Investment processed successfully"
        }), 200
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return jsonify({"error": "Invalid input data"}), 400
    except Exception as e:
        logger.error(f"Investment processing failed: {e}")
        return jsonify({"error": "Investment processing failed"}), 500

@app.route('/api/v1/portfolio/<user_id>', methods=['GET'])
def get_portfolio(user_id):
    """Get user portfolio information."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, user_id, total_value, currency, tier1_allocation, tier2_allocation, tier3_allocation,
                   tier1_value, tier2_value, tier3_value, created_at, updated_at
            FROM user_portfolios 
            WHERE user_id = %s
        """, (user_id,))
        
        portfolio = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not portfolio:
            return jsonify({"error": "Portfolio not found"}), 404
        
        # Convert to serializable format
        portfolio_data = {
            "id": str(portfolio['id']),
            "user_id": portfolio['user_id'],
            "total_value": float(portfolio['total_value']),
            "currency": portfolio['currency'],
            "tier1_allocation": float(portfolio['tier1_allocation']),
            "tier2_allocation": float(portfolio['tier2_allocation']),
            "tier3_allocation": float(portfolio['tier3_allocation']),
            "tier1_value": float(portfolio['tier1_value']),
            "tier2_value": float(portfolio['tier2_value']),
            "tier3_value": float(portfolio['tier3_value']),
            "created_at": portfolio['created_at'].isoformat(),
            "updated_at": portfolio['updated_at'].isoformat()
        }
        
        return jsonify(portfolio_data), 200
        
    except Exception as e:
        logger.error(f"Failed to get portfolio: {e}")
        return jsonify({"error": "Failed to retrieve portfolio"}), 500

@app.route('/api/v1/portfolio/<user_id>/transactions', methods=['GET'])
def get_portfolio_transactions(user_id):
    """Get user portfolio transactions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get portfolio ID first
        cursor.execute("SELECT id FROM user_portfolios WHERE user_id = %s", (user_id,))
        portfolio = cursor.fetchone()
        
        if not portfolio:
            return jsonify({"error": "Portfolio not found"}), 404
        
        portfolio_id = str(portfolio['id'])
        
        # Get transactions
        cursor.execute("""
            SELECT id, transaction_type, tier1_change, tier2_change, tier3_change,
                   total_amount, fees, status, created_at, updated_at
            FROM portfolio_transactions 
            WHERE portfolio_id = %s 
            ORDER BY created_at DESC
            LIMIT 50
        """, (portfolio_id,))
        
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
        
        return jsonify(transaction_list), 200
        
    except Exception as e:
        logger.error(f"Failed to get portfolio transactions: {e}")
        return jsonify({"error": "Failed to retrieve transactions"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)