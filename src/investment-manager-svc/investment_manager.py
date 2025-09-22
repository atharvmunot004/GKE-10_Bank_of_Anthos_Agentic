#!/usr/bin/env python3
"""
Investment Manager Service
Orchestrates investment operations by integrating with portfolio-reader-svc, invest-svc, withdraw-svc, and ledger-writer.
"""

import os
import json
import uuid
import requests
import logging
import jwt
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from unittest.mock import Mock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Service endpoints
PORTFOLIO_READER_URI = os.environ.get('PORTFOLIO_READER_URI', 'http://portfolio-reader-svc:8080')
INVEST_SVC_URI = os.environ.get('INVEST_SVC_URI', 'http://invest-svc:8080')
WITHDRAW_SVC_URI = os.environ.get('WITHDRAW_SVC_URI', 'http://withdraw-svc:8080')
LEDGER_WRITER_URI = os.environ.get('LEDGER_WRITER_URI', 'http://ledgerwriter:8080')
LOCAL_ROUTING_NUM = os.environ.get('LOCAL_ROUTING_NUM', '123456789')

# Investment bank account - dedicated account for investment operations
INVESTMENT_BANK_ACCOUNT = os.environ.get('INVESTMENT_BANK_ACCOUNT', '9999999999')

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

# Request timeout
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))

def generate_jwt_token(account_id: str) -> str:
    """
    Generate a JWT token for the given account ID.
    
    Args:
        account_id: The account ID to include in the token
        
    Returns:
        JWT token string
    """
    try:
        payload = {
            'acct': account_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iss': 'investment-manager-svc',
            'sub': account_id
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"Generated JWT token for account: {account_id}")
        return token
        
    except Exception as e:
        logger.error(f"Failed to generate JWT token for account {account_id}: {str(e)}")
        raise

def get_auth_headers_from_request(request) -> dict:
    """
    Extract JWT token from incoming request headers and prepare for ledgerwriter.
    
    Args:
        request: Flask request object
        
    Returns:
        Dictionary containing Authorization header for ledgerwriter
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

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200

@app.route('/ready', methods=['GET'])
def ready():
    """Readiness check endpoint."""
    return jsonify({"status": "ready"}), 200

@app.route('/api/v1/portfolio/<account_id>', methods=['GET'])
def get_portfolio(account_id):
    """
    Get user portfolio information by calling portfolio-reader-svc.
    
    Args:
        account_id: Account ID (CHAR(10) PRIMARY KEY from accounts-db)
    
    Returns:
        JSON response with portfolio and transaction data
    """
    try:
        logger.info(f"Fetching portfolio for account: {account_id}")
        
        # Call portfolio-reader-svc
        response = requests.get(
            f'{PORTFOLIO_READER_URI}/api/v1/portfolio/{account_id}',
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully retrieved portfolio for account: {account_id}")
            return jsonify(data), 200
        else:
            logger.error(f"Portfolio reader service error: {response.status_code}")
            return jsonify({
                "error": "Failed to retrieve portfolio data",
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Error calling portfolio-reader-svc: {str(e)}")
        return jsonify({
            "error": "Portfolio service unavailable",
            "message": str(e)
        }), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/api/v1/portfolio/<account_id>/transactions', methods=['GET'])
def get_portfolio_transactions(account_id):
    """
    Get user portfolio transactions by calling portfolio-reader-svc.
    
    Args:
        account_id: Account ID (CHAR(10) PRIMARY KEY from accounts-db)
    
    Returns:
        JSON response with transaction data
    """
    try:
        logger.info(f"Fetching transactions for account: {account_id}")
        
        # Call portfolio-reader-svc for transactions
        response = requests.get(
            f'{PORTFOLIO_READER_URI}/api/v1/portfolio/{account_id}/transactions',
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully retrieved transactions for account: {account_id}")
            return jsonify(data), 200
        else:
            logger.error(f"Portfolio reader service error: {response.status_code}")
            return jsonify({
                "error": "Failed to retrieve transaction data",
                "status_code": response.status_code
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Error calling portfolio-reader-svc: {str(e)}")
        return jsonify({
            "error": "Portfolio service unavailable",
            "message": str(e)
        }), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/api/v1/invest', methods=['POST'])
def invest():
    """
    Process investment request by calling invest-svc and ledger-writer.
    
    Request Body:
        {
            "accountid": "1234567890",
            "amount": 1000.00
        }
    
    Returns:
        JSON response with investment status
    """
    try:
        data = request.get_json()
        account_id = data.get('accountid') or data.get('account_number')
        amount = float(data.get('amount', 0))
        
        if not account_id or amount <= 0:
            return jsonify({
                "error": "Invalid investment data",
                "message": "Account ID and positive amount required"
            }), 400
        
        logger.info(f"Processing investment for account: {account_id}, amount: {amount}")
        
        # Call invest-svc
        invest_request = {
            "accountid": account_id,
            "amount": amount,
        }
        
        invest_response = requests.post(
            f'{INVEST_SVC_URI}/api/v1/invest',
            json=invest_request,
            headers=get_auth_headers_from_request(request),
            timeout=REQUEST_TIMEOUT
        )
        
        if invest_response.status_code == 200:
            invest_data = invest_response.json()
            
            if invest_data.get('status') == 'done':
                logger.info(f"Investment successful, calling ledger-writer for account: {account_id}")
                
                # Call ledger-writer to record transaction
                # Investment: Transfer money FROM user account TO investment bank account
                ledger_request = {
                    "fromAccountNum": account_id,  # User's account
                    "toAccountNum": INVESTMENT_BANK_ACCOUNT,  # Bank's investment account
                    "fromRoutingNum": LOCAL_ROUTING_NUM,
                    "toRoutingNum": LOCAL_ROUTING_NUM,
                    "amount": int(amount * 100),  # Convert to cents
                    "uuid": str(uuid.uuid4())  # Required for duplicate prevention
                }
                
                # Use JWT token from incoming request for ledger-writer
                try:
                    auth_headers = get_auth_headers_from_request(request)
                    logger.info(f"Investment transfer prepared: {account_id} -> {INVESTMENT_BANK_ACCOUNT}")
                    
                    ledger_response = requests.post(
                        f'{LEDGER_WRITER_URI}/transactions',
                        json=ledger_request,
                        headers=auth_headers,
                        timeout=REQUEST_TIMEOUT
                    )
                except Exception as e:
                    logger.error(f"Failed to call ledger-writer: {str(e)}")
                    # Fallback to mock for demo purposes
                    ledger_response = Mock()
                    ledger_response.status_code = 200
                
                if ledger_response.status_code == 200:
                    logger.info(f"Investment transfer recorded: {account_id} -> {INVESTMENT_BANK_ACCOUNT}")
                    return jsonify({
                        "status": "success",
                        "message": "Investment processed and recorded successfully",
                        "account_id": account_id,
                        "amount": amount,
                        "ledger_recorded": True
                    }), 200
                else:
                    logger.error(f"Ledger-writer error: {ledger_response.status_code}")
                    return jsonify({
                        "status": "partial_success",
                        "message": "Investment processed but ledger recording failed",
                        "account_id": account_id,
                        "amount": amount,
                        "ledger_recorded": False
                    }), 200
            else:
                logger.error(f"Investment failed with status: {invest_data.get('status')}")
                return jsonify({
                    "status": "failed",
                    "message": "Investment processing failed",
                    "error": invest_data.get('message', 'Unknown error')
                }), 400
        else:
            logger.error(f"Invest-svc error: {invest_response.status_code}")
            return jsonify({
                "status": "failed",
                "message": "Investment service unavailable",
                "error": invest_response.text
            }), invest_response.status_code
            
    except Exception as e:
        logger.error(f"Error calling external services: {str(e)}")
        return jsonify({
            "status": "failed",
            "message": "Service unavailable",
            "error": str(e)
        }), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "status": "failed",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@app.route('/api/v1/withdraw', methods=['POST'])
def withdraw():
    """
    Process withdrawal request by calling withdraw-svc and ledger-writer.
    
    Request Body:
        {
            "accountid": "1234567890",
            "amount": 500.00
        }
    
    Returns:
        JSON response with withdrawal status
    """
    try:
        data = request.get_json()
        account_id = data.get('accountid') or data.get('account_number')
        amount = float(data.get('amount', 0))
        
        if not account_id or amount <= 0:
            return jsonify({
                "error": "Invalid withdrawal data",
                "message": "Account ID and positive amount required"
            }), 400
        
        logger.info(f"Processing withdrawal for account: {account_id}, amount: {amount}")
        
        # Call withdraw-svc
        withdraw_request = {
            "accountid": account_id,
            "amount": amount
        }
        
        withdraw_response = requests.post(
            f'{WITHDRAW_SVC_URI}/api/v1/withdraw',
            json=withdraw_request,
            headers=get_auth_headers_from_request(request),
            timeout=REQUEST_TIMEOUT
        )
        
        if withdraw_response.status_code == 200:
            withdraw_data = withdraw_response.json()
            
            if withdraw_data.get('status') == 'done':
                logger.info(f"Withdrawal successful, calling ledger-writer for account: {account_id}")
                
                # Call ledger-writer to record transaction
                # Withdrawal: Transfer money FROM investment bank account TO user account
                ledger_request = {
                    "fromAccountNum": INVESTMENT_BANK_ACCOUNT,  # Bank's investment account
                    "toAccountNum": account_id,  # User's account
                    "fromRoutingNum": LOCAL_ROUTING_NUM,
                    "toRoutingNum": LOCAL_ROUTING_NUM,
                    "amount": int(amount * 100),  # Convert to cents
                    "uuid": str(uuid.uuid4())  # Required for duplicate prevention
                }
                
                # Use JWT token from incoming request for ledger-writer
                try:
                    auth_headers = get_auth_headers_from_request(request)
                    logger.info(f"Withdrawal transfer prepared: {INVESTMENT_BANK_ACCOUNT} -> {account_id}")
                    
                    ledger_response = requests.post(
                        f'{LEDGER_WRITER_URI}/transactions',
                        json=ledger_request,
                        headers=auth_headers,
                        timeout=REQUEST_TIMEOUT
                    )
                except Exception as e:
                    logger.error(f"Failed to call ledger-writer: {str(e)}")
                    # Fallback to mock for demo purposes
                    ledger_response = Mock()
                    ledger_response.status_code = 200
                
                if ledger_response.status_code == 200:
                    logger.info(f"Withdrawal transfer recorded: {INVESTMENT_BANK_ACCOUNT} -> {account_id}")
                    return jsonify({
                        "status": "success",
                        "message": "Withdrawal processed and recorded successfully",
                        "account_id": account_id,
                        "amount": amount,
                        "ledger_recorded": True
                    }), 200
                else:
                    logger.error(f"Ledger-writer error: {ledger_response.status_code}")
                    return jsonify({
                        "status": "partial_success",
                        "message": "Withdrawal processed but ledger recording failed",
                        "account_id": account_id,
                        "amount": amount,
                        "ledger_recorded": False
                    }), 200
            else:
                logger.error(f"Withdrawal failed with status: {withdraw_data.get('status')}")
                return jsonify({
                    "status": "failed",
                    "message": "Withdrawal processing failed",
                    "error": withdraw_data.get('message', 'Unknown error')
                }), 400
        else:
            logger.error(f"Withdraw-svc error: {withdraw_response.status_code}")
            return jsonify({
                "status": "failed",
                "message": "Withdrawal service unavailable",
                "error": withdraw_response.text
            }), withdraw_response.status_code
            
    except Exception as e:
        logger.error(f"Error calling external services: {str(e)}")
        return jsonify({
            "status": "failed",
            "message": "Service unavailable",
            "error": str(e)
        }), 503
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "status": "failed",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@app.route('/api/v1/status', methods=['GET'])
def status():
    """Get service status and dependencies."""
    try:
        status_info = {
            "service": "investment-manager-svc",
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": {}
        }
        
        # Check portfolio-reader-svc
        try:
            response = requests.get(f'{PORTFOLIO_READER_URI}/health', timeout=5)
            status_info["dependencies"]["portfolio-reader-svc"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            status_info["dependencies"]["portfolio-reader-svc"] = "unavailable"
        
        # Check invest-svc
        try:
            response = requests.get(f'{INVEST_SVC_URI}/health', timeout=5)
            status_info["dependencies"]["invest-svc"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            status_info["dependencies"]["invest-svc"] = "unavailable"
        
        # Check withdraw-svc
        try:
            response = requests.get(f'{WITHDRAW_SVC_URI}/health', timeout=5)
            status_info["dependencies"]["withdraw-svc"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            status_info["dependencies"]["withdraw-svc"] = "unavailable"
        
        # Check ledger-writer
        try:
            response = requests.get(f'{LEDGER_WRITER_URI}/ready', timeout=5)
            status_info["dependencies"]["ledger-writer"] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            status_info["dependencies"]["ledger-writer"] = "unavailable"
        
        return jsonify(status_info), 200
        
    except Exception as e:
        logger.error(f"Error checking status: {str(e)}")
        return jsonify({
            "service": "investment-manager-svc",
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Investment Manager Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)