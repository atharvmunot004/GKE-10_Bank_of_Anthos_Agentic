#!/usr/bin/env python3
"""
User Tier Agent Service

AI-powered agent that analyzes user transaction history and intelligently
allocates investment amounts across three tiers based on liquidity preferences.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
LEDGER_DB_URI = os.environ.get('LEDGER_DB_URI', 'postgresql://postgres:postgres@ledger-db:5432/postgresdb')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_API_URL = os.environ.get('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent')
PORT = int(os.environ.get('PORT', 8080))
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))

class UserTierAgent:
    """AI-powered agent for intelligent tier allocation."""
    
    def __init__(self):
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_api_url = GEMINI_API_URL
        self.ledger_db_uri = LEDGER_DB_URI
        
    def get_db_connection(self):
        """Get database connection to ledger-db."""
        try:
            conn = psycopg2.connect(self.ledger_db_uri)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to ledger-db: {e}")
            raise
    
    def validate_jwt_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token and extract account information."""
        try:
            if not token.startswith('Bearer '):
                return None
            
            token = token.split(' ', 1)[1]
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT token")
            return None
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}")
            return None
    
    def get_user_transaction_history(self, account_id: str, limit: int = 50) -> List[Dict]:
        """Query ledger-db for recent user transactions."""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
            SELECT amount, timestamp, fromAccountNum, toAccountNum, uuid
            FROM transactions 
            WHERE fromAccountNum = %s OR toAccountNum = %s
            ORDER BY timestamp DESC 
            LIMIT %s
            """
            
            cursor.execute(query, (account_id, account_id, limit))
            transactions = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(transactions)} transactions for account {account_id}")
            return [dict(transaction) for transaction in transactions]
            
        except Exception as e:
            logger.error(f"Error retrieving transaction history: {e}")
            raise
    
    def format_transaction_data(self, transactions: List[Dict]) -> List[Tuple[float, str]]:
        """Convert transaction data to format expected by AI agent."""
        formatted_data = []
        
        for transaction in transactions:
            amount = float(transaction['amount']) / 100  # Convert cents to dollars
            timestamp = transaction['timestamp'].isoformat()
            formatted_data.append((amount, timestamp))
        
        return formatted_data
    
    def generate_tier_allocation_prompt(self, uuid: str, transaction_data: List[Tuple[float, str]], amount_break: float) -> str:
        """Generate the prompt for Gemini AI."""
        
        # Create transaction history string
        transaction_history = ",\n".join([f"[{amount}, {timestamp}]" for amount, timestamp in transaction_data])
        
        prompt = f"""You are a smart allocation agent that gets {{
    uuid: "{uuid}",
    transaction_history: [
        {transaction_history}
    ],
    amount_break: {amount_break}
}} and has to divide amount_break into 3 tiers, where:
- Tier1 is the most liquid (cash-like investments, money market funds, short-term bonds)
- Tier2 is moderately liquid (balanced funds, ETFs, medium-term investments)  
- Tier3 is the least liquid (long-term investments, growth funds, real estate)

Based on the transaction history of this user, analyze their spending patterns, transaction frequency, and amount patterns to determine the optimal allocation.

Consider:
- Transaction frequency (how often they transact)
- Transaction amounts (average, median, range)
- Spending patterns (consistent vs variable)
- Recent transaction trends
- Risk tolerance indicators from transaction behavior

Return ONLY a JSON response in this exact format:
{{
    "tier1": <percentage as float>,
    "tier2": <percentage as float>, 
    "tier3": <percentage as float>,
    "reasoning": "<brief explanation of allocation decision>"
}}

The percentages must sum to exactly 100.0.
"""
        return prompt
    
    def call_gemini_api(self, prompt: str) -> Dict:
        """Call Gemini API to get tier allocation recommendation."""
        try:
            if not self.gemini_api_key:
                logger.warning("Gemini API key not configured, using default allocation")
                return self.get_default_allocation()
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 500,
                    "topP": 0.8,
                    "topK": 10
                }
            }
            
            url = f"{self.gemini_api_url}?key={self.gemini_api_key}"
            
            response = requests.post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the generated text
            if 'candidates' in result and len(result['candidates']) > 0:
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                # Try to parse JSON from the response
                try:
                    # Extract JSON from the response text
                    json_start = generated_text.find('{')
                    json_end = generated_text.rfind('}') + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_text = generated_text[json_start:json_end]
                        allocation = json.loads(json_text)
                        
                        # Validate the response
                        if self.validate_allocation_response(allocation):
                            logger.info(f"Received valid allocation from Gemini: {allocation}")
                            return allocation
                        else:
                            logger.warning("Invalid allocation from Gemini, using default")
                            return self.get_default_allocation()
                    else:
                        logger.warning("No JSON found in Gemini response")
                        return self.get_default_allocation()
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Gemini JSON response: {e}")
                    return self.get_default_allocation()
            else:
                logger.warning("No candidates in Gemini response")
                return self.get_default_allocation()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Gemini API: {e}")
            return self.get_default_allocation()
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini API: {e}")
            return self.get_default_allocation()
    
    def validate_allocation_response(self, allocation: Dict) -> bool:
        """Validate the allocation response from Gemini."""
        try:
            required_keys = ['tier1', 'tier2', 'tier3']
            
            # Check if all required keys are present
            if not all(key in allocation for key in required_keys):
                return False
            
            # Check if values are numeric
            if not all(isinstance(allocation[key], (int, float)) for key in required_keys):
                return False
            
            # Check if percentages sum to 100
            total = allocation['tier1'] + allocation['tier2'] + allocation['tier3']
            if abs(total - 100.0) > 0.1:  # Allow small floating point errors
                return False
            
            # Check if all percentages are positive
            if not all(allocation[key] >= 0 for key in required_keys):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating allocation response: {e}")
            return False
    
    def get_default_allocation(self) -> Dict:
        """Get default tier allocation when AI is unavailable."""
        return {
            "tier1": 30.0,
            "tier2": 50.0,
            "tier3": 20.0,
            "reasoning": "Default allocation: conservative distribution due to AI unavailability"
        }
    
    def calculate_tier_amounts(self, amount_break: float, allocation: Dict) -> Dict:
        """Calculate actual dollar amounts for each tier."""
        tier1_amount = (amount_break * allocation['tier1']) / 100.0
        tier2_amount = (amount_break * allocation['tier2']) / 100.0
        tier3_amount = (amount_break * allocation['tier3']) / 100.0
        
        return {
            "tier1": round(tier1_amount, 2),
            "tier2": round(tier2_amount, 2),
            "tier3": round(tier3_amount, 2)
        }
    
    def process_allocation_request(self, request_data: Dict, jwt_token: str) -> Dict:
        """Process a tier allocation request."""
        try:
            # Validate JWT token
            token_payload = self.validate_jwt_token(jwt_token)
            if not token_payload:
                raise ValueError("Invalid or expired JWT token")
            
            # Extract request parameters
            account_id = request_data.get('accountid')
            amount_break = float(request_data.get('amount', 0))
            uuid = request_data.get('uuid')
            purpose = request_data.get('purpose', 'INVEST')
            
            if not account_id or amount_break <= 0 or not uuid:
                raise ValueError("Missing required parameters: accountid, amount, uuid")
            
            # Verify account ID matches JWT token
            if token_payload.get('account') != account_id:
                raise ValueError("Account ID does not match JWT token")
            
            logger.info(f"Processing allocation request for account {account_id}, amount {amount_break}, UUID {uuid}")
            
            # Step 1: Get transaction history
            transactions = self.get_user_transaction_history(account_id)
            
            # Step 2: Format transaction data
            formatted_data = self.format_transaction_data(transactions)
            
            # Step 3: Generate prompt and call Gemini
            prompt = self.generate_tier_allocation_prompt(uuid, formatted_data, amount_break)
            allocation = self.call_gemini_api(prompt)
            
            # Calculate tier amounts
            tier_amounts = self.calculate_tier_amounts(amount_break, allocation)
            
            # Prepare response
            response = {
                "accountid": account_id,
                "amount": amount_break,
                "uuid": uuid,
                "purpose": purpose,
                "tier1": tier_amounts["tier1"],
                "tier2": tier_amounts["tier2"],
                "tier3": tier_amounts["tier3"],
                "allocation_percentages": {
                    "tier1": allocation["tier1"],
                    "tier2": allocation["tier2"],
                    "tier3": allocation["tier3"]
                },
                "reasoning": allocation.get("reasoning", "AI-generated allocation"),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Successfully processed allocation: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing allocation request: {e}")
            raise

# Initialize the agent
tier_agent = UserTierAgent()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "user-tier-agent"}), 200

@app.route('/ready', methods=['GET'])
def readiness():
    """Readiness probe endpoint."""
    try:
        # Test database connectivity
        conn = tier_agent.get_db_connection()
        conn.close()
        
        return jsonify({
            "status": "ready",
            "service": "user-tier-agent",
            "checks": {
                "database": "connected",
                "gemini_api": "configured" if GEMINI_API_KEY else "not_configured"
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "not ready",
            "service": "user-tier-agent",
            "error": str(e)
        }), 503

@app.route('/api/v1/allocate', methods=['POST'])
def allocate_tiers():
    """Main endpoint for tier allocation."""
    try:
        # Get JWT token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401
        
        # Get request data
        request_data = request.get_json()
        if not request_data:
            return jsonify({"error": "Missing request body"}), 400
        
        # Process the allocation request
        result = tier_agent.process_allocation_request(request_data, auth_header)
        
        return jsonify({
            "status": "success",
            "data": result
        }), 200
        
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error in allocate_tiers endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/v1/status', methods=['GET'])
def get_status():
    """Get service status and configuration."""
    return jsonify({
        "status": "operational",
        "service": "user-tier-agent",
        "version": "1.0.0",
        "configuration": {
            "gemini_api_configured": bool(GEMINI_API_KEY),
            "database_uri": LEDGER_DB_URI.split('@')[1] if '@' in LEDGER_DB_URI else "configured",
            "jwt_algorithm": JWT_ALGORITHM
        },
        "endpoints": {
            "allocate": "/api/v1/allocate",
            "health": "/health",
            "ready": "/ready",
            "status": "/api/v1/status"
        }
    }), 200

if __name__ == '__main__':
    logger.info(f"Starting User Tier Agent service on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
