"""
LangChain tools for the tier allocation agent
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain.tools import tool

from app.core.config import settings
from app.models.schemas import Transaction

logger = structlog.get_logger(__name__)


@tool
def collect_user_transaction_history(accountid: str, limit: int = 100) -> str:
    """
    Collect user transaction history from ledger-db.
    
    Args:
        accountid: The account identifier
        limit: Number of transactions to fetch (default: 100)
    
    Returns:
        JSON string containing list of transactions
    """
    try:
        logger.info("Collecting transaction history", accountid=accountid, limit=limit)
        
        # Make HTTP request to ledger-db
        response = httpx.get(
            f"{settings.LEDGER_DB_URL}/transactions/{accountid}",
            params={"limit": limit},
            timeout=30.0
        )
        response.raise_for_status()
        
        transactions_data = response.json()
        
        # Convert to the expected format
        transactions = []
        for tx in transactions_data.get("transactions", []):
            transaction = {
                "TRANSACTION_ID": tx.get("transaction_id", ""),
                "FROM_ACCT": tx.get("from_acct", ""),
                "TO_ACCT": tx.get("to_acct", ""),
                "FROM_ROUTE": tx.get("from_route", ""),
                "TO_ROUTE": tx.get("to_route", ""),
                "AMOUNT": tx.get("amount", 0.0),
                "TIMESTAMP": tx.get("timestamp", "")
            }
            transactions.append(transaction)
        
        result = {
            "transactions": transactions,
            "count": len(transactions),
            "accountid": accountid
        }
        
        logger.info("Transaction history collected", count=len(transactions))
        return json.dumps(result)
        
    except httpx.HTTPError as e:
        error_msg = f"HTTP error collecting transaction history: {str(e)}"
        logger.error(error_msg, accountid=accountid)
        return json.dumps({"error": error_msg, "transactions": []})
    except Exception as e:
        error_msg = f"Error collecting transaction history: {str(e)}"
        logger.error(error_msg, accountid=accountid)
        return json.dumps({"error": error_msg, "transactions": []})


@tool
def publish_allocation_to_queue(
    uuid: str,
    accountid: str,
    tier1: float,
    tier2: float,
    tier3: float,
    purpose: str
) -> str:
    """
    Publish tier allocation to queue-db.
    
    Args:
        uuid: Request UUID
        accountid: Account identifier
        tier1: Tier 1 allocation amount
        tier2: Tier 2 allocation amount
        tier3: Tier 3 allocation amount
        purpose: Purpose of allocation (INVEST or WITHDRAW)
    
    Returns:
        JSON string with success/failure status
    """
    try:
        logger.info("Publishing allocation to queue", uuid=uuid, accountid=accountid)
        
        payload = {
            "uuid": uuid,
            "accountid": accountid,
            "tier1": tier1,
            "tier2": tier2,
            "tier3": tier3,
            "purpose": purpose
        }
        
        response = httpx.post(
            f"{settings.QUEUE_DB_URL}/allocations",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        
        result = response.json()
        
        logger.info("Allocation published to queue successfully", uuid=uuid)
        return json.dumps({"success": True, "result": result})
        
    except httpx.HTTPError as e:
        error_msg = f"HTTP error publishing to queue: {str(e)}"
        logger.error(error_msg, uuid=uuid)
        return json.dumps({"success": False, "error": error_msg})
    except Exception as e:
        error_msg = f"Error publishing to queue: {str(e)}"
        logger.error(error_msg, uuid=uuid)
        return json.dumps({"success": False, "error": error_msg})


@tool
def add_transaction_to_portfolio_db(
    uuid: str,
    accountid: str,
    tier1: float,
    tier2: float,
    tier3: float,
    purpose: str
) -> str:
    """
    Add transaction to portfolio database.
    
    Args:
        uuid: Request UUID
        accountid: Account identifier
        tier1: Tier 1 allocation amount
        tier2: Tier 2 allocation amount
        tier3: Tier 3 allocation amount
        purpose: Purpose of allocation (INVEST or WITHDRAW)
    
    Returns:
        JSON string with success/failure status
    """
    try:
        logger.info("Adding transaction to portfolio DB", uuid=uuid, accountid=accountid)
        
        payload = {
            "uuid": uuid,
            "accountid": accountid,
            "tier1": tier1,
            "tier2": tier2,
            "tier3": tier3,
            "purpose": purpose,
            "table": "portfolio-transactions-tb"
        }
        
        response = httpx.post(
            f"{settings.PORTFOLIO_DB_URL}/portfolio-transactions",
            json=payload,
            timeout=30.0
        )
        response.raise_for_status()
        
        result = response.json()
        
        logger.info("Transaction added to portfolio DB successfully", uuid=uuid)
        return json.dumps({"success": True, "result": result})
        
    except httpx.HTTPError as e:
        error_msg = f"HTTP error adding to portfolio DB: {str(e)}"
        logger.error(error_msg, uuid=uuid)
        return json.dumps({"success": False, "error": error_msg})
    except Exception as e:
        error_msg = f"Error adding to portfolio DB: {str(e)}"
        logger.error(error_msg, uuid=uuid)
        return json.dumps({"success": False, "error": error_msg})


# Tool instances for the agent
collect_user_transaction_history_tool = collect_user_transaction_history
publish_allocation_to_queue_tool = publish_allocation_to_queue
add_transaction_to_portfolio_db_tool = add_transaction_to_portfolio_db
