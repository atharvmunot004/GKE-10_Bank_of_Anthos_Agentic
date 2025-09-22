import os
import uuid
import logging
import psycopg2
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
USER_PORTFOLIO_DB_URI = os.environ.get('USER_PORTFOLIO_DB_URI', 'postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db')
USER_TIER_AGENT_URI = os.environ.get('USER_TIER_AGENT_URI', 'http://user-tier-agent:8080')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(USER_PORTFOLIO_DB_URI)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def get_auth_headers_from_request(req):
    """Extract authorization headers from incoming request."""
    headers = {}
    auth_header = req.headers.get('Authorization')
    if auth_header:
        headers['Authorization'] = auth_header
    
    # Forward account ID header if present
    account_id = req.headers.get('x-auth-account-id')
    if account_id:
        headers['x-auth-account-id'] = account_id
    
    headers['Content-Type'] = 'application/json'
    return headers

def check_portfolio_value(account_id: str) -> float:
    """Check the total portfolio value for an account."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT total_value 
            FROM user_portfolios 
            WHERE accountid = %s
        """, (account_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return float(result['total_value'])
        else:
            return 0.0
            
    except Exception as e:
        logger.error(f"Failed to check portfolio value: {e}")
        raise

def get_tier_allocation(account_id: str, amount: float, auth_headers: dict) -> dict:
    """Get tier allocation from user-tier-agent for withdrawal."""
    try:
        withdrawal_uuid = str(uuid.uuid4())
        
        request_data = {
            "accountid": account_id,
            "amount": amount,
            "uuid": withdrawal_uuid,
            "purpose": "WITHDRAW"
        }
        
        logger.info(f"Getting tier allocation for withdrawal: account {account_id}, amount {amount}")
        
        response = requests.post(
            f'{USER_TIER_AGENT_URI}/allocate',
            json=request_data,
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

def create_withdrawal_transaction(account_id: str, amount: float, tier_data: dict, withdrawal_uuid: str) -> str:
    """Create withdrawal transaction record."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO portfolio_transactions (
                accountid, transaction_type, tier1_change, tier2_change, tier3_change,
                total_amount, fees, status, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            ) RETURNING id
        """, (
            account_id,
            'WITHDRAWAL',
            -float(tier_data['tier1']),  # Negative values for withdrawal
            -float(tier_data['tier2']),
            -float(tier_data['tier3']),
            amount,
            0.0,  # No fees for withdrawal
            'PENDING'
        ))
        
        transaction_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Created withdrawal transaction {transaction_id}")
        return str(transaction_id)
        
    except Exception as e:
        logger.error(f"Failed to create withdrawal transaction: {e}")
        raise

def update_portfolio_values(account_id: str, tier_data: dict) -> bool:
    """Update portfolio values after withdrawal."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current portfolio values
        cursor.execute("""
            SELECT tier1_value, tier2_value, tier3_value, total_value
            FROM user_portfolios 
            WHERE accountid = %s
        """, (account_id,))
        
        portfolio = cursor.fetchone()
        if not portfolio:
            raise Exception(f"Portfolio not found for account {account_id}")
        
        # Calculate new values (subtract withdrawal amounts)
        new_tier1_value = float(portfolio['tier1_value']) - float(tier_data['tier1'])
        new_tier2_value = float(portfolio['tier2_value']) - float(tier_data['tier2'])
        new_tier3_value = float(portfolio['tier3_value']) - float(tier_data['tier3'])
        new_total_value = new_tier1_value + new_tier2_value + new_tier3_value
        
        # Update portfolio values
        cursor.execute("""
            UPDATE user_portfolios 
            SET 
                tier1_value = %s,
                tier2_value = %s,
                tier3_value = %s,
                total_value = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE accountid = %s
        """, (new_tier1_value, new_tier2_value, new_tier3_value, new_total_value, account_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated portfolio values for account {account_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update portfolio values: {e}")
        raise

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
        
        # Check external service connectivity
        try:
            response = requests.get(f'{USER_TIER_AGENT_URI}/health', timeout=5)
            if response.status_code != 200:
                raise Exception(f"User tier agent health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return jsonify({"status": "not ready", "error": str(e)}), 500
        
        return jsonify({"status": "ready"}), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 500

@app.route('/api/v1/withdraw', methods=['POST'])
def withdraw():
    """
    Process withdrawal request.
    
    Request Body:
        {
            "accountid": "1234567890",
            "amount": 1000.00
        }
    
    Returns:
        JSON response with withdrawal status
    """
    try:
        data = request.get_json()
        account_id = data.get('accountid')
        amount = float(data.get('amount', 0))
        
        if not account_id or amount <= 0:
            return jsonify({
                "status": "failed",
                "error": "Invalid withdrawal data",
                "message": "Account ID and positive amount required"
            }), 400
        
        logger.info(f"Processing withdrawal for account: {account_id}, amount: {amount}")
        
        # Check if portfolio has sufficient value
        total_value = check_portfolio_value(account_id)
        if total_value < amount:
            logger.warning(f"Insufficient portfolio value for account {account_id}: {total_value} < {amount}")
            return jsonify({
                "status": "failed",
                "error": "Insufficient portfolio value",
                "message": f"Portfolio value {total_value} is less than withdrawal amount {amount}"
            }), 400
        
        logger.info(f"Portfolio value check passed: {total_value} >= {amount}")
        
        # Get tier allocation from user-tier-agent
        auth_headers = get_auth_headers_from_request(request)
        tier_data = get_tier_allocation(account_id, amount, auth_headers)
        
        # Create withdrawal transaction
        withdrawal_uuid = tier_data.get('uuid', str(uuid.uuid4()))
        transaction_id = create_withdrawal_transaction(account_id, amount, tier_data, withdrawal_uuid)
        
        # Update portfolio values
        update_portfolio_values(account_id, tier_data)
        
        logger.info(f"Withdrawal processed successfully for account {account_id}")
        
        return jsonify({
            "status": "done",
            "accountid": account_id,
            "amount": amount,
            "uuid": withdrawal_uuid,
            "tier1": float(tier_data['tier1']),
            "tier2": float(tier_data['tier2']),
            "tier3": float(tier_data['tier3']),
            "transaction_id": transaction_id,
            "message": "Withdrawal processed successfully"
        }), 200
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return jsonify({
            "status": "failed",
            "error": "Invalid input data"
        }), 400
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Withdraw Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
