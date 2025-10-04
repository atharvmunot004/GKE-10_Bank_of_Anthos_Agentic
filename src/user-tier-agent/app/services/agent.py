"""
Tier Allocation Agent using LangChain and Gemini
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
import structlog
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.models.schemas import TierAllocation, TierAllocationRequest, Transaction
from app.services.tools import (
    collect_user_transaction_history_tool,
    publish_allocation_to_queue_tool,
    add_transaction_to_portfolio_db_tool
)

logger = structlog.get_logger(__name__)


class TierAllocationAgent:
    """Main tier allocation agent using LangChain and Gemini"""
    
    def __init__(self):
        self.llm = None
        self.agent_executor = None
        self.tools = []
        self._initialize_llm()
        self._initialize_tools()
        self._initialize_agent()
    
    def _initialize_llm(self):
        """Initialize the Gemini LLM"""
        try:
            self.llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                timeout=settings.LLM_TIMEOUT
            )
            logger.info("Gemini LLM initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Gemini LLM", error=str(e))
            raise
    
    def _initialize_tools(self):
        """Initialize the tools for the agent"""
        self.tools = [
            collect_user_transaction_history_tool,
            publish_allocation_to_queue_tool,
            add_transaction_to_portfolio_db_tool
        ]
        logger.info("Tools initialized", count=len(self.tools))
    
    def _initialize_agent(self):
        """Initialize the agent with tools and prompt"""
        try:
            # Create the prompt template
            prompt = PromptTemplate(
                input_variables=["input", "agent_scratchpad"],
                template=self._get_agent_prompt()
            )
            
            # Create the agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create the agent executor
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=10,
                handle_parsing_errors=True
            )
            
            logger.info("Agent executor initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize agent executor", error=str(e))
            raise
    
    def _get_agent_prompt(self) -> str:
        """Get the agent prompt template"""
        return """You are a 'Financial Tier Allocation Agent'. Your primary goal is to intelligently split a user's investment or withdrawal amount into three financial tiers based on their transaction history.

Tier Definitions:
    a. Tier 1: Money invested in this tier is the most liquid. It can be withdrawn almost instantaneously in conditions of urgent money requirements / emergencies. Money invested in this tier is invested with the purpose that a sudden unexpected requirement of money can be fulfilled.

    b. Tier 2: Money invested in this tier is moderately liquid. It can be withdrawn within a timespan of atmost 15 days (a fortnight) for purposes of planned / monthly / recurring payments. Money is invested in this tier considering these steady / regular expenses.

    c. Tier 3: Money invested in this tier is the least liquid and is meant for purposes of long term investments. The money invested in this tier is invested with the purpose of building a strong and steady wealth spanning over the lifetime of the user. Money may be withdrawn from this tier but it usually is meant to be non-volatile and meant to compound over a period of few years. Unless an unexpected expense of huge amount comes into the picture, money is not to be withdrawn from this tier.

Your process would be as follows:
1. You will receive a request in the form of a JSON payload: {{uuid, accountid, amount, purpose: 'WITHDRAW' / 'INVEST'}} from either of the two microservices: a) invest-svc, b) withdraw-svc,
2. First, you must decide how many transactions (N) you need to analyze to understand the user's spending habits (expense trends). A good starting point is 100, but adjust if you think more or less data is needed,
3. call the collect_user_transaction_history tool with 'accountid' and chosen 'N',
4. analyse the transaction history provided by the tool. Look for patterns: 
    a. frequent small purchases (daily life), 
    b. large monthly debits (rent/bills),
    c. large infrequent credits / debits (investments / salary),
    Additionally consider nuances, one example being: If a user's spending is erratic, then he / she would require more investment in tier1. Similarly, by the same logic during withdrawal, he / she would withdraw more from tier1 as well.
5. Based on this analysis, calculate the split for the user's request amount into tier1, tier2, and tier3. Crucially, the sum of tier1, tier2, and tier3 must exactly equal the original 'amount' in the request. Provide your reasoning.
6. Once you have the final allocation, call the publish_allocation_to_queue tool with all the required information.
7. After successfully publishing to the queue, you must also save the transaction by calling the add_transaction_to_portfolio_db tool with the same information. This is a mandatory final step.

Error Handling: If any tool fails or returns an error, do not try again. Your task is to report the failure clearly. For example: 'The collect_user_transaction_history tool failed to connect to the database.'

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""
    
    async def allocate_tiers(self, request: TierAllocationRequest) -> TierAllocation:
        """Allocate tiers for the given request"""
        try:
            logger.info(
                "Starting tier allocation",
                uuid=request.uuid,
                accountid=request.accountid,
                amount=request.amount,
                purpose=request.purpose
            )
            
            # Prepare input for the agent
            agent_input = {
                "uuid": request.uuid,
                "accountid": request.accountid,
                "amount": request.amount,
                "purpose": request.purpose
            }
            
            # Execute the agent
            result = await asyncio.to_thread(
                self.agent_executor.invoke,
                {"input": json.dumps(agent_input)},
                config={"callbacks": []}
            )
            
            # Parse the result
            allocation = self._parse_agent_result(result, request.amount)
            
            logger.info(
                "Tier allocation completed",
                uuid=request.uuid,
                allocation=allocation.model_dump()
            )
            
            return allocation
            
        except Exception as e:
            logger.error(
                "Tier allocation failed",
                uuid=request.uuid,
                error=str(e)
            )
            raise
    
    def _parse_agent_result(self, result: Dict[str, Any], total_amount: float) -> TierAllocation:
        """Parse the agent result and create tier allocation"""
        try:
            # Extract the final answer from the agent result
            final_answer = result.get("output", "")
            
            # Try to extract tier allocation from the final answer
            # This is a simplified parsing - in production, you might want more robust parsing
            lines = final_answer.strip().split('\n')
            
            tier1 = tier2 = tier3 = 0.0
            
            for line in lines:
                line = line.strip().lower()
                if 'tier1' in line or 'tier 1' in line:
                    # Extract number from line
                    import re
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        tier1 = float(numbers[0])
                elif 'tier2' in line or 'tier 2' in line:
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        tier2 = float(numbers[0])
                elif 'tier3' in line or 'tier 3' in line:
                    numbers = re.findall(r'\d+\.?\d*', line)
                    if numbers:
                        tier3 = float(numbers[0])
            
            # If parsing failed or amounts don't add up, use default allocation
            if abs(tier1 + tier2 + tier3 - total_amount) > 0.01:
                logger.warning(
                    "Agent result parsing failed or amounts don't match, using default allocation",
                    parsed_tiers=[tier1, tier2, tier3],
                    total_amount=total_amount
                )
                
                # Use default percentages
                tier1 = total_amount * (settings.DEFAULT_TIER1_PERCENTAGE / 100)
                tier2 = total_amount * (settings.DEFAULT_TIER2_PERCENTAGE / 100)
                tier3 = total_amount * (settings.DEFAULT_TIER3_PERCENTAGE / 100)
            
            return TierAllocation(tier1=tier1, tier2=tier2, tier3=tier3)
            
        except Exception as e:
            logger.error("Failed to parse agent result", error=str(e))
            # Return default allocation as fallback
            tier1 = total_amount * (settings.DEFAULT_TIER1_PERCENTAGE / 100)
            tier2 = total_amount * (settings.DEFAULT_TIER2_PERCENTAGE / 100)
            tier3 = total_amount * (settings.DEFAULT_TIER3_PERCENTAGE / 100)
            
            return TierAllocation(tier1=tier1, tier2=tier2, tier3=tier3)
    
    async def get_default_allocation(self, amount: float) -> TierAllocation:
        """Get default tier allocation for new users"""
        tier1 = amount * (settings.DEFAULT_TIER1_PERCENTAGE / 100)
        tier2 = amount * (settings.DEFAULT_TIER2_PERCENTAGE / 100)
        tier3 = amount * (settings.DEFAULT_TIER3_PERCENTAGE / 100)
        
        return TierAllocation(tier1=tier1, tier2=tier2, tier3=tier3)


# Global agent instance
tier_allocation_agent = TierAllocationAgent()
