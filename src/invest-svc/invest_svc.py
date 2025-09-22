import os
import json
import uuid
import requests
import logging
import psycopg2
from datetime import datetime
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service endpoints
USER_PORTFOLIO_DB_URI = os.environ.get('USER_PORTFOLIO_DB_URI', 'postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db')
USER_TIER_AGENT_URI = os.environ.get('USER_TIER_AGENT_URI', 'http://user-tier-agent:8080')
BALANCE_READER_URI = os.environ.get('BALANCE_READER_URI', 'http://balancereader:8080')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(USER_PORTFOLIO_DB_URI)

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

def get_tier_allocation(account_id: str, amount: float, auth_headers: dict) -> dict:
    """
    Get tier allocation from user-tier-agent.
    
    Args:
        account_id: Account number
        amount: Investment amount
        auth_headers: Authorization headers with JWT token
        
    Returns:
        Tier allocation data
    """
    try:
        # Generate UUID for this request
        request_uuid = str(uuid.uuid4())
        
        payload = {
            "accountid": account_id,
            "amount": amount,
            "uuid": request_uuid,
            "purpose": "INVEST"
        }
        
        response = requests.post(
            f'{USER_TIER_AGENT_URI}/allocate',
            json=payload,
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

def check_balance(account_id: str, amount: float, auth_headers: dict) -> bool:
    """
    Check if account has sufficient balance for investment.
    
    Args:
        account_id: Account number
        amount: Investment amount
        auth_headers: Authorization headers with JWT token
        
    Returns:
        True if sufficient balance, False otherwise
    """
    try:
        response = requests.get(
            f'{BALANCE_READER_URI}/balances/{account_id}',
            headers=auth_headers,
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            balance_data = response.json()
            current_balance = balance_data.get('balance', 0)
            logger.info(f"Account {account_id} balance: {current_balance}")
            
            if current_balance >= amount:
                return True
            else:
                logger.warning(f"Insufficient balance for account {account_id}: {current_balance} < {amount}")
                return False
        else:
            logger.error(f"Failed to get balance: {response.status_code}")
            raise Exception(f"Balance check failed: {response.text}")
            
    except Exception as e:
        logger.error(f"Error checking balance: {e}")
        raise

def update_portfolio_allocations(account_id: str, tier_data: dict) -> bool:
    """
    Update user portfolio allocations.
    
    Args:
        account_id: Account number
        tier_data: Tier allocation data from user-tier-agent
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if portfolio exists
        cursor.execute("""
            SELECT accountid, tier1_allocation, tier2_allocation, tier3_allocation
            FROM user_portfolios 
            WHERE accountid = %s
        """, (account_id,))
        
        portfolio = cursor.fetchone()
        
        if portfolio:
            # Update existing portfolio allocations
            new_tier1_allocation = float(portfolio['tier1_allocation']) + float(tier_data['tier1'])
            new_tier2_allocation = float(portfolio['tier2_allocation']) + float(tier_data['tier2'])
            new_tier3_allocation = float(portfolio['tier3_allocation']) + float(tier_data['tier3'])
            new_total_allocation = new_tier1_allocation + new_tier2_allocation + new_tier3_allocation
            
            cursor.execute("""
                UPDATE user_portfolios 
                SET 
                    tier1_allocation = %s,
                    tier2_allocation = %s,
                    tier3_allocation = %s,
                    total_allocation = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE accountid = %s
            """, (new_tier1_allocation, new_tier2_allocation, new_tier3_allocation, 
                  new_total_allocation, account_id))
            
            logger.info(f"Updated existing portfolio allocations for {account_id}")
            
        else:
            # Create new portfolio with initial allocations
            total_amount = float(tier_data['tier1']) + float(tier_data['tier2']) + float(tier_data['tier3'])
            
            cursor.execute("""
                INSERT INTO user_portfolios (
                    accountid, currency, tier1_allocation, tier2_allocation, tier3_allocation, 
                    total_allocation, tier1_value, tier2_value, tier3_value, total_value,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """, (account_id, 'USD',
                  tier_data['tier1'], tier_data['tier2'], tier_data['tier3'], total_amount,
                  0, 0, 0, 0))
            
            logger.info(f"Created new portfolio with allocations for {account_id}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update portfolio allocations: {e}")
        return False

def create_portfolio_transaction(account_id: str, amount: float, tier_data: dict, request_uuid: str) -> str:
    """
    Create portfolio transaction record.
    
    Args:
        account_id: Account number
        amount: Investment amount
        tier_data: Tier allocation data
        request_uuid: UUID for this transaction
        
    Returns:
        Transaction ID
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        transaction_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO portfolio_transactions (
                id, accountid, transaction_type, tier1_change, tier2_change, tier3_change,
                total_amount, status, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """, (transaction_id, account_id, 'INVEST',
              tier_data['tier1'], tier_data['tier2'], tier_data['tier3'],
              amount, 'PENDING'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Created portfolio transaction {transaction_id}")
        return transaction_id
        
    except Exception as e:
        logger.error(f"Failed to create portfolio transaction: {e}")
        raise

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
        
        # Also check external services if needed
        requests.get(f'{USER_TIER_AGENT_URI}/health', timeout=REQUEST_TIMEOUT).raise_for_status()
        requests.get(f'{BALANCE_READER_URI}/health', timeout=REQUEST_TIMEOUT).raise_for_status()
        
        return jsonify({"status": "ready"}), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 500

@app.route('/api/v1/invest', methods=['POST'])
def invest():
    """Process investment request."""
    try:
        # Get account ID from headers
        account_id = request.headers.get('x-auth-account-id')
        if not account_id:
            return jsonify({"error": "Account ID not provided"}), 401
        
        # Get request data
        data = request.get_json()
        amount = float(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({"error": "Invalid investment amount"}), 400
        
        logger.info(f"Processing investment for account {account_id}, amount: {amount}")
        
        # Get auth headers for external service calls
        auth_headers = get_auth_headers_from_request(request)
        
        # Step 1: Check balance
        logger.info(f"Checking balance for account {account_id}")
        if not check_balance(account_id, amount, auth_headers):
            return jsonify({
                "status": "failed", 
                "message": "Insufficient balance for investment"
            }), 400
        
        # Step 2: Get tier allocation
        logger.info(f"Getting tier allocation for account {account_id}")
        tier_data = get_tier_allocation(account_id, amount, auth_headers)
        
        # Step 3: Create portfolio transaction
        request_uuid = tier_data.get('uuid', str(uuid.uuid4()))
        transaction_id = create_portfolio_transaction(account_id, amount, tier_data, request_uuid)
        
        # Step 4: Update portfolio allocations
        if not update_portfolio_allocations(account_id, tier_data):
            return jsonify({
                "status": "failed",
                "message": "Failed to update portfolio allocations"
            }), 500
        
        logger.info(f"Investment processed successfully for account {account_id}")
        
        return jsonify({
            "status": "done",
            "accountid": account_id,
            "amount": amount,
            "uuid": request_uuid,
            "tier1": float(tier_data['tier1']),
            "tier2": float(tier_data['tier2']),
            "tier3": float(tier_data['tier3']),
            "transaction_id": transaction_id,
            "message": "Investment processed successfully"
        }), 200
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return jsonify({"error": "Invalid input data"}), 400
    except Exception as e:
        logger.error(f"Error processing investment: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/portfolio/<string:user_id>', methods=['GET'])
def get_portfolio(user_id):
    """Get user portfolio information."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT accountid, currency, tier1_allocation, tier2_allocation, tier3_allocation, 
                   total_allocation, tier1_value, tier2_value, tier3_value, total_value,
                   created_at, updated_at
            FROM user_portfolios 
            WHERE accountid = %s
        """, (user_id,))
        
        portfolio = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not portfolio:
            return jsonify({"error": "Portfolio not found"}), 404
        
        # Convert to serializable format
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
        
        return jsonify(portfolio_data), 200
        
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 8080))
