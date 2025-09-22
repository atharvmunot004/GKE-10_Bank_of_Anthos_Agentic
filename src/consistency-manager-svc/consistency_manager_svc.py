import os
import logging
import psycopg2
from flask import Flask, request, jsonify
from psycopg2.extras import RealDictCursor
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
QUEUE_DB_URI = os.environ.get('QUEUE_DB_URI', 'postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db')
USER_PORTFOLIO_DB_URI = os.environ.get('USER_PORTFOLIO_DB_URI', 'postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db')
POLLING_INTERVAL = int(os.environ.get('POLLING_INTERVAL', '30'))

# Tier environment variables
TIER1 = float(os.environ.get('TIER1', '1000000.0'))
TIER1_MV = float(os.environ.get('TIER1_MV', '1000000.0'))
TIER2 = float(os.environ.get('TIER2', '2000000.0'))
TIER2_MV = float(os.environ.get('TIER2_MV', '2000000.0'))
TIER3 = float(os.environ.get('TIER3', '500000.0'))
TIER3_MV = float(os.environ.get('TIER3_MV', '500000.0'))

# Global variables for consistency management
last_timestamp = datetime.now()
processing_lock = threading.Lock()

def get_queue_db_connection():
    """Get connection to queue-db."""
    try:
        conn = psycopg2.connect(QUEUE_DB_URI)
        return conn
    except Exception as e:
        logger.error(f"Queue database connection failed: {e}")
        raise

def get_portfolio_db_connection():
    """Get connection to user-portfolio-db."""
    try:
        conn = psycopg2.connect(USER_PORTFOLIO_DB_URI)
        return conn
    except Exception as e:
        logger.error(f"Portfolio database connection failed: {e}")
        raise

def calculate_delta_values():
    """Step1: Calculate delta values for tier market value changes."""
    global TIER1, TIER1_MV, TIER2, TIER2_MV, TIER3, TIER3_MV
    
    try:
        # Calculate delta values
        del_t1_mv = ((TIER1_MV - TIER1) / TIER1) if TIER1 != 0 else 0
        del_t2_mv = ((TIER2_MV - TIER2) / TIER2) if TIER2 != 0 else 0
        del_t3_mv = ((TIER3_MV - TIER3) / TIER3) if TIER3 != 0 else 0
        
        logger.info(f"Calculated delta values: del_t1_mv={del_t1_mv:.4f}, del_t2_mv={del_t2_mv:.4f}, del_t3_mv={del_t3_mv:.4f}")
        
        return {
            'del_t1_mv': del_t1_mv,
            'del_t2_mv': del_t2_mv,
            'del_t3_mv': del_t3_mv
        }
    except Exception as e:
        logger.error(f"Error calculating delta values: {e}")
        return {'del_t1_mv': 0, 'del_t2_mv': 0, 'del_t3_mv': 0}

def get_updated_investment_queue_entries(timestamp):
    """Step2: Get investment queue entries updated after timestamp."""
    try:
        conn = get_queue_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT uuid, accountid, status, updated_at
            FROM investment_queue 
            WHERE updated_at > %s
            ORDER BY updated_at ASC
        """, (timestamp,))
        
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(entries)} updated investment queue entries")
        return entries
        
    except Exception as e:
        logger.error(f"Error getting investment queue entries: {e}")
        return []

def get_updated_withdrawal_queue_entries(timestamp):
    """Step5: Get withdrawal queue entries updated after timestamp."""
    try:
        conn = get_queue_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT uuid, accountid, status, updated_at
            FROM withdrawal_queue 
            WHERE updated_at > %s
            ORDER BY updated_at ASC
        """, (timestamp,))
        
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Found {len(entries)} updated withdrawal queue entries")
        return entries
        
    except Exception as e:
        logger.error(f"Error getting withdrawal queue entries: {e}")
        return []

def update_portfolio_transaction_status(uuids, status):
    """Step3 & Step6: Update portfolio transaction status."""
    try:
        conn = get_portfolio_db_connection()
        cursor = conn.cursor()
        
        for uuid_val in uuids:
            cursor.execute("""
                UPDATE portfolio_transactions 
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE uuid = %s
            """, (status, uuid_val))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated portfolio transaction status to {status} for {len(uuids)} entries")
        return True
        
    except Exception as e:
        logger.error(f"Error updating portfolio transaction status: {e}")
        return False

def update_portfolio_tier_values(accountid, del_t1_mv, del_t2_mv, del_t3_mv, operation='invest'):
    """Step4 & Step7: Update portfolio tier values based on market changes."""
    try:
        conn = get_portfolio_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current portfolio values
        cursor.execute("""
            SELECT tier1_value, tier2_value, tier3_value, tier1_allocation, tier2_allocation, tier3_allocation
            FROM user_portfolios 
            WHERE accountid = %s
        """, (accountid,))
        
        portfolio = cursor.fetchone()
        if not portfolio:
            logger.warning(f"Portfolio not found for accountid: {accountid}")
            cursor.close()
            conn.close()
            return False
        
        # Calculate new values based on operation
        if operation == 'invest':
            # For investments: update tier values
            new_tier1_value = portfolio['tier1_value'] * (1 + del_t1_mv)
            new_tier2_value = portfolio['tier2_value'] * (1 + del_t2_mv)
            new_tier3_value = portfolio['tier3_value'] * (1 + del_t3_mv)
            
            cursor.execute("""
                UPDATE user_portfolios 
                SET tier1_value = %s, tier2_value = %s, tier3_value = %s,
                    total_value = %s, updated_at = CURRENT_TIMESTAMP
                WHERE accountid = %s
            """, (new_tier1_value, new_tier2_value, new_tier3_value, 
                  new_tier1_value + new_tier2_value + new_tier3_value, accountid))
                  
        else:  # withdrawal
            # For withdrawals: update tier allocations
            new_tier1_allocation = portfolio['tier1_allocation'] * (1 - del_t1_mv)
            new_tier2_allocation = portfolio['tier2_allocation'] * (1 - del_t2_mv)
            new_tier3_allocation = portfolio['tier3_allocation'] * (1 - del_t3_mv)
            
            cursor.execute("""
                UPDATE user_portfolios 
                SET tier1_allocation = %s, tier2_allocation = %s, tier3_allocation = %s,
                    total_allocation = %s, updated_at = CURRENT_TIMESTAMP
                WHERE accountid = %s
            """, (new_tier1_allocation, new_tier2_allocation, new_tier3_allocation,
                  new_tier1_allocation + new_tier2_allocation + new_tier3_allocation, accountid))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated portfolio for accountid {accountid} with {operation} operation")
        return True
        
    except Exception as e:
        logger.error(f"Error updating portfolio tier values: {e}")
        return False

def process_investment_queue_entries(entries, delta_values):
    """Process investment queue entries (Steps 3-4)."""
    try:
        completed_uuids = []
        all_uuids = []
        
        for entry in entries:
            uuid_val = entry['uuid']
            accountid = entry['accountid']
            status = entry['status']
            
            all_uuids.append(uuid_val)
            
            # Step3: Update portfolio transaction status
            if status == 'COMPLETED':
                completed_uuids.append((uuid_val, accountid))
        
        # Update portfolio transaction statuses
        if all_uuids:
            update_portfolio_transaction_status(all_uuids, 'PROCESSED')
        
        # Step4: Update portfolio tier values for completed entries
        for uuid_val, accountid in completed_uuids:
            update_portfolio_tier_values(
                accountid, 
                delta_values['del_t1_mv'], 
                delta_values['del_t2_mv'], 
                delta_values['del_t3_mv'],
                'invest'
            )
        
        logger.info(f"Processed {len(all_uuids)} investment queue entries, {len(completed_uuids)} completed")
        return len(all_uuids), len(completed_uuids)
        
    except Exception as e:
        logger.error(f"Error processing investment queue entries: {e}")
        return 0, 0

def process_withdrawal_queue_entries(entries, delta_values):
    """Process withdrawal queue entries (Steps 6-7)."""
    try:
        completed_uuids = []
        all_uuids = []
        
        for entry in entries:
            uuid_val = entry['uuid']
            accountid = entry['accountid']
            status = entry['status']
            
            all_uuids.append(uuid_val)
            
            # Step6: Update portfolio transaction status
            if status == 'COMPLETED':
                completed_uuids.append((uuid_val, accountid))
        
        # Update portfolio transaction statuses
        if all_uuids:
            update_portfolio_transaction_status(all_uuids, 'PROCESSED')
        
        # Step7: Update portfolio tier allocations for completed entries
        for uuid_val, accountid in completed_uuids:
            update_portfolio_tier_values(
                accountid, 
                delta_values['del_t1_mv'], 
                delta_values['del_t2_mv'], 
                delta_values['del_t3_mv'],
                'withdrawal'
            )
        
        logger.info(f"Processed {len(all_uuids)} withdrawal queue entries, {len(completed_uuids)} completed")
        return len(all_uuids), len(completed_uuids)
        
    except Exception as e:
        logger.error(f"Error processing withdrawal queue entries: {e}")
        return 0, 0

def consistency_cycle():
    """Main consistency management cycle."""
    global last_timestamp, TIER1, TIER1_MV, TIER2, TIER2_MV, TIER3, TIER3_MV
    
    with processing_lock:
        try:
            logger.info("Starting consistency management cycle")
            
            # Step1: Calculate delta values
            delta_values = calculate_delta_values()
            
            # Step2: Get updated investment queue entries
            investment_entries = get_updated_investment_queue_entries(last_timestamp)
            
            # Steps 3-4: Process investment queue entries
            inv_processed, inv_completed = process_investment_queue_entries(investment_entries, delta_values)
            
            # Step5: Get updated withdrawal queue entries
            withdrawal_entries = get_updated_withdrawal_queue_entries(last_timestamp)
            
            # Steps 6-7: Process withdrawal queue entries
            wd_processed, wd_completed = process_withdrawal_queue_entries(withdrawal_entries, delta_values)
            
            # Step8: Update timestamp
            last_timestamp = datetime.now()
            
            logger.info(f"Consistency cycle completed: {inv_processed} investment entries ({inv_completed} completed), {wd_processed} withdrawal entries ({wd_completed} completed)")
            
            return {
                'status': 'success',
                'timestamp': last_timestamp.isoformat(),
                'delta_values': delta_values,
                'investment_processed': inv_processed,
                'investment_completed': inv_completed,
                'withdrawal_processed': wd_processed,
                'withdrawal_completed': wd_completed
            }
            
        except Exception as e:
            logger.error(f"Error in consistency cycle: {e}")
            return {'status': 'error', 'error': str(e)}

def background_consistency_manager():
    """Background thread for continuous consistency management."""
    while True:
        try:
            result = consistency_cycle()
            logger.info(f"Consistency cycle result: {result['status']}")
            time.sleep(POLLING_INTERVAL)
        except Exception as e:
            logger.error(f"Error in background consistency manager: {e}")
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
        queue_conn = get_queue_db_connection()
        queue_cursor = queue_conn.cursor()
        queue_cursor.execute("SELECT 1")
        queue_cursor.close()
        queue_conn.close()
        
        portfolio_conn = get_portfolio_db_connection()
        portfolio_cursor = portfolio_conn.cursor()
        portfolio_cursor.execute("SELECT 1")
        portfolio_cursor.close()
        portfolio_conn.close()
        
        return jsonify({"status": "ready"}), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 500

@app.route('/api/v1/consistency/status', methods=['GET'])
def get_consistency_status():
    """Get current consistency management status."""
    try:
        delta_values = calculate_delta_values()
        
        return jsonify({
            "status": "success",
            "timestamp": last_timestamp.isoformat(),
            "tier_values": {
                "TIER1": TIER1,
                "TIER1_MV": TIER1_MV,
                "TIER2": TIER2,
                "TIER2_MV": TIER2_MV,
                "TIER3": TIER3,
                "TIER3_MV": TIER3_MV
            },
            "delta_values": delta_values,
            "polling_interval": POLLING_INTERVAL
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting consistency status: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

@app.route('/api/v1/consistency/trigger', methods=['POST'])
def trigger_consistency_cycle():
    """Manually trigger a consistency cycle."""
    try:
        result = consistency_cycle()
        
        return jsonify(result), 200 if result['status'] == 'success' else 500
        
    except Exception as e:
        logger.error(f"Error triggering consistency cycle: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/v1/consistency/update-tier-values', methods=['POST'])
def update_tier_values():
    """Update tier values from external sources."""
    global TIER1, TIER1_MV, TIER2, TIER2_MV, TIER3, TIER3_MV
    
    try:
        data = request.get_json()
        
        if 'TIER1' in data:
            TIER1 = float(data['TIER1'])
            os.environ['TIER1'] = str(TIER1)
        if 'TIER1_MV' in data:
            TIER1_MV = float(data['TIER1_MV'])
            os.environ['TIER1_MV'] = str(TIER1_MV)
        if 'TIER2' in data:
            TIER2 = float(data['TIER2'])
            os.environ['TIER2'] = str(TIER2)
        if 'TIER2_MV' in data:
            TIER2_MV = float(data['TIER2_MV'])
            os.environ['TIER2_MV'] = str(TIER2_MV)
        if 'TIER3' in data:
            TIER3 = float(data['TIER3'])
            os.environ['TIER3'] = str(TIER3)
        if 'TIER3_MV' in data:
            TIER3_MV = float(data['TIER3_MV'])
            os.environ['TIER3_MV'] = str(TIER3_MV)
        
        logger.info(f"Updated tier values: TIER1={TIER1}, TIER1_MV={TIER1_MV}, TIER2={TIER2}, TIER2_MV={TIER2_MV}, TIER3={TIER3}, TIER3_MV={TIER3_MV}")
        
        return jsonify({
            "status": "success",
            "updated_tier_values": {
                "TIER1": TIER1,
                "TIER1_MV": TIER1_MV,
                "TIER2": TIER2,
                "TIER2_MV": TIER2_MV,
                "TIER3": TIER3,
                "TIER3_MV": TIER3_MV
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating tier values: {e}")
        return jsonify({
            "status": "failed",
            "error": str(e)
        }), 500

# Start background consistency manager thread
def start_background_consistency_manager():
    """Start the background consistency manager thread."""
    manager_thread = threading.Thread(target=background_consistency_manager, daemon=True)
    manager_thread.start()
    logger.info("Background consistency manager thread started")

if __name__ == '__main__':
    # Start background consistency manager
    start_background_consistency_manager()
    
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting Consistency Manager Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
