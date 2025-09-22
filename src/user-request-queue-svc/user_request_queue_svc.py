import os
import logging
import psycopg2
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
import requests
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
QUEUE_DB_URI = os.environ.get('QUEUE_DB_URI', 'postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db')
BANK_ASSET_AGENT_URI = os.environ.get('BANK_ASSET_AGENT_URI', 'http://bank-asset-agent:8080')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '30'))
POLLING_INTERVAL = int(os.environ.get('POLLING_INTERVAL', '5'))

# Global variables for batch processing
request_queue = []
processing_lock = threading.Lock()

def get_db_connection():
    """Get database connection."""
    try:
        conn = psycopg2.connect(QUEUE_DB_URI)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def add_request_to_queue(uuid_val, tier1, tier2, tier3, purpose, accountid=None):
    """Add request to queue-db with PROCESSING status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO withdrawal_queue (
                uuid, accountid, tier1, tier2, tier3, purpose, status, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """, (uuid_val, accountid, tier1, tier2, tier3, purpose, 'PROCESSING'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Added request {uuid_val} to queue with status PROCESSING")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add request to queue: {e}")
        raise

def get_pending_requests():
    """Get up to BATCH_SIZE pending requests from queue-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT uuid, accountid, tier1, tier2, tier3, purpose
            FROM withdrawal_queue 
            WHERE status = 'PROCESSING'
            ORDER BY created_at ASC
            LIMIT %s
        """, (BATCH_SIZE,))
        
        requests_data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Retrieved {len(requests_data)} pending requests")
        return requests_data
        
    except Exception as e:
        logger.error(f"Failed to get pending requests: {e}")
        raise

def calculate_aggregate_tiers(requests_data):
    """Calculate aggregate tier values from requests."""
    T1 = 0
    T2 = 0
    T3 = 0
    
    for req in requests_data:
        if req['purpose'] == 'INVEST':
            T1 += float(req['tier1'])
            T2 += float(req['tier2'])
            T3 += float(req['tier3'])
        elif req['purpose'] == 'WITHDRAW':
            T1 -= float(req['tier1'])
            T2 -= float(req['tier2'])
            T3 -= float(req['tier3'])
    
    logger.info(f"Calculated aggregate tiers: T1={T1}, T2={T2}, T3={T3}")
    return T1, T2, T3

def call_bank_asset_agent(T1, T2, T3):
    """Make request to bank-asset-agent with aggregate tier values."""
    try:
        payload = {
            "T1": T1,
            "T2": T2,
            "T3": T3
        }
        
        logger.info(f"Calling bank-asset-agent with payload: {payload}")
        
        response = requests.post(
            f'{BANK_ASSET_AGENT_URI}/process',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=REQUEST_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('status', 'FAILED')
            logger.info(f"Bank-asset-agent response: {status}")
            return status
        else:
            logger.error(f"Bank-asset-agent error: {response.status_code}")
            return 'FAILED'
            
    except Exception as e:
        logger.error(f"Failed to call bank-asset-agent: {e}")
        return 'FAILED'

def update_request_status(uuid_list, status):
    """Update status of requests in queue-db."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update status for all UUIDs in the list
        for uuid_val in uuid_list:
            cursor.execute("""
                UPDATE withdrawal_queue 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE uuid = %s
            """, (status, uuid_val))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated status to {status} for {len(uuid_list)} requests")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update request status: {e}")
        raise

def process_batch():
    """Process a batch of pending requests."""
    with processing_lock:
        try:
            # Get pending requests
            requests_data = get_pending_requests()
            
            if len(requests_data) < BATCH_SIZE:
                logger.info(f"Only {len(requests_data)} requests available, waiting for more")
                return
            
            logger.info(f"Processing batch of {len(requests_data)} requests")
            
            # Calculate aggregate tiers
            T1, T2, T3 = calculate_aggregate_tiers(requests_data)
            
            # Call bank-asset-agent
            status = call_bank_asset_agent(T1, T2, T3)
            
            # Update request statuses
            uuid_list = [req['uuid'] for req in requests_data]
            update_request_status(uuid_list, status)
            
            logger.info(f"Batch processing completed with status: {status}")
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            # Update any requests that were being processed to FAILED
            try:
                requests_data = get_pending_requests()
                if requests_data:
                    uuid_list = [req['uuid'] for req in requests_data]
                    update_request_status(uuid_list, 'FAILED')
            except Exception as update_error:
                logger.error(f"Failed to update failed requests: {update_error}")

def background_processor():
    """Background thread to process batches periodically."""
    while True:
        try:
            process_batch()
            time.sleep(POLLING_INTERVAL)
        except Exception as e:
            logger.error(f"Error in background processor: {e}")
            time.sleep(POLLING_INTERVAL)

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
            response = requests.get(f'{BANK_ASSET_AGENT_URI}/health', timeout=5)
            if response.status_code != 200:
                raise Exception(f"Bank asset agent health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return jsonify({"status": "not ready", "error": str(e)}), 500
        
        return jsonify({"status": "ready"}), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 500

@app.route('/api/v1/queue', methods=['POST'])
def add_to_queue():
    """
    Add request to processing queue.
    
    Request Body:
        {
            "uuid": "request-uuid",
            "tier1": 600.0,
            "tier2": 300.0,
            "tier3": 100.0,
            "purpose": "INVEST" or "WITHDRAW",
            "accountid": "1234567890" (optional)
        }
    
    Returns:
        JSON response with queue status
    """
    try:
        data = request.get_json()
        uuid_val = data.get('uuid')
        tier1 = float(data.get('tier1', 0))
        tier2 = float(data.get('tier2', 0))
        tier3 = float(data.get('tier3', 0))
        purpose = data.get('purpose')
        accountid = data.get('accountid')
        
        if not uuid_val or not purpose:
            return jsonify({
                "status": "failed",
                "error": "Missing required fields",
                "message": "UUID and purpose are required"
            }), 400
        
        if purpose not in ['INVEST', 'WITHDRAW']:
            return jsonify({
                "status": "failed",
                "error": "Invalid purpose",
                "message": "Purpose must be 'INVEST' or 'WITHDRAW'"
            }), 400
        
        logger.info(f"Adding request to queue: {uuid_val}, purpose: {purpose}")
        
        # Add request to queue-db
        add_request_to_queue(uuid_val, tier1, tier2, tier3, purpose, accountid)
        
        return jsonify({
            "status": "queued",
            "uuid": uuid_val,
            "message": "Request added to processing queue"
        }), 200
        
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return jsonify({
            "status": "failed",
            "error": "Invalid input data"
        }), 400
    except Exception as e:
        logger.error(f"Error adding to queue: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

@app.route('/api/v1/queue/status/<uuid>', methods=['GET'])
def get_queue_status(uuid):
    """
    Get status of a request in the queue.
    
    Returns:
        JSON response with request status
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT uuid, accountid, tier1, tier2, tier3, purpose, status, created_at, updated_at
            FROM withdrawal_queue 
            WHERE uuid = %s
        """, (uuid,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({
                "uuid": result['uuid'],
                "accountid": result['accountid'],
                "tier1": float(result['tier1']),
                "tier2": float(result['tier2']),
                "tier3": float(result['tier3']),
                "purpose": result['purpose'],
                "status": result['status'],
                "created_at": result['created_at'].isoformat(),
                "updated_at": result['updated_at'].isoformat()
            }), 200
        else:
            return jsonify({
                "status": "not_found",
                "message": f"Request {uuid} not found in queue"
            }), 404
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

@app.route('/api/v1/queue/stats', methods=['GET'])
def get_queue_stats():
    """Get queue statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing,
                COUNT(CASE WHEN status = 'DONE' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed
            FROM withdrawal_queue
        """)
        
        stats = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            "total_requests": stats['total_requests'],
            "processing": stats['processing'],
            "completed": stats['completed'],
            "failed": stats['failed']
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

# Start background processor thread
def start_background_processor():
    """Start the background processor thread."""
    processor_thread = threading.Thread(target=background_processor, daemon=True)
    processor_thread.start()
    logger.info("Background processor thread started")

if __name__ == '__main__':
    # Start background processor
    start_background_processor()
    
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting User Request Queue Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
