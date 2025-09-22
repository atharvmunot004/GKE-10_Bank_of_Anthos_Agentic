#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - AI-Powered Server

import os
import sys
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import json

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.ai_market_analyzer import AIMarketAnalyzer
from tools.ai_decision_maker import AIDecisionMaker
from tools.ai_portfolio_manager import AIPortfolioManager
from tools.market_analyzer import MarketAnalyzer
from utils.http_client import MarketReaderClient, RuleCheckerClient, ExecuteOrderClient
from utils.db_client import AssetsDatabaseClient
from ai.gemini_client import GeminiAIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize AI components
try:
    gemini_client = GeminiAIClient()
    ai_market_analyzer = AIMarketAnalyzer(gemini_client)
    ai_decision_maker = AIDecisionMaker(gemini_client)
    ai_portfolio_manager = AIPortfolioManager(gemini_client)
    market_analyzer = MarketAnalyzer(ai_analyzer=ai_market_analyzer)
    
    # Initialize service clients
    market_reader_client = MarketReaderClient()
    rule_checker_client = RuleCheckerClient()
    execute_order_client = ExecuteOrderClient()
    
    # Initialize database clients
    assets_db_client = AssetsDatabaseClient(os.environ.get('ASSETS_DB_URI'))
    
    logger.info("AI-powered Bank Asset Agent initialized successfully")
    
except Exception as e:
    logger.error(f"Failed to initialize AI components: {e}")
    # Fallback to non-AI mode
    ai_market_analyzer = None
    ai_decision_maker = None
    ai_portfolio_manager = None
    market_analyzer = MarketAnalyzer()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'ai_enabled': ai_market_analyzer is not None,
        'version': os.environ.get('VERSION', 'dev')
    })


@app.route('/api/v1/market/analyze', methods=['POST'])
def analyze_market():
    """Analyze market data using AI"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        time_range = data.get('time_range', '1d')
        
        # Get market data
        market_data = market_reader_client.get_market_data(symbols, time_range)
        
        # Analyze with AI
        if ai_market_analyzer:
            analysis = ai_market_analyzer.analyze_market_trends(market_data)
        else:
            analysis = market_analyzer.analyze_trends(market_data)
        
        return jsonify({
            'status': 'success',
            'analysis': analysis,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Market analysis failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/market/predict', methods=['POST'])
def predict_prices():
    """Predict asset prices using AI"""
    try:
        data = request.get_json()
        historical_data = data.get('historical_data', [])
        horizon = data.get('horizon', '1h')
        
        # Predict with AI
        if ai_market_analyzer:
            predictions = ai_market_analyzer.predict_asset_prices(historical_data, horizon)
        else:
            predictions = market_analyzer.predict_prices(historical_data, horizon)
        
        return jsonify({
            'status': 'success',
            'predictions': predictions,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Price prediction failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/investment/decide', methods=['POST'])
def make_investment_decision():
    """Make AI-powered investment decision"""
    try:
        data = request.get_json()
        investment_request = data.get('investment_request', {})
        market_data = data.get('market_data', {})
        user_profile = data.get('user_profile', {})
        risk_rules = data.get('risk_rules', {})
        
        if not ai_decision_maker:
            return jsonify({
                'status': 'error',
                'message': 'AI decision making not available',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
        
        # Make AI decision
        decision = ai_decision_maker.make_investment_decision(
            investment_request, market_data, user_profile, risk_rules
        )
        
        return jsonify({
            'status': 'success',
            'decision': decision,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Investment decision failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/portfolio/optimize', methods=['POST'])
def optimize_portfolio():
    """Optimize portfolio using AI"""
    try:
        data = request.get_json()
        current_portfolio = data.get('current_portfolio', {})
        market_conditions = data.get('market_conditions', {})
        user_goals = data.get('user_goals', {})
        risk_tolerance = data.get('risk_tolerance', 'medium')
        
        if not ai_portfolio_manager:
            return jsonify({
                'status': 'error',
                'message': 'AI portfolio optimization not available',
                'timestamp': datetime.utcnow().isoformat()
            }), 503
        
        # Optimize portfolio with AI
        optimization = ai_portfolio_manager.optimize_portfolio(
            current_portfolio, market_conditions, user_goals, risk_tolerance
        )
        
        return jsonify({
            'status': 'success',
            'optimization': optimization,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Portfolio optimization failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/assets', methods=['GET'])
def get_assets():
    """Get available assets from database"""
    try:
        tier = request.args.get('tier')
        
        if tier:
            assets = assets_db_client.get_assets_by_tier(int(tier))
        else:
            assets = assets_db_client.get_all_assets()
        
        return jsonify({
            'status': 'success',
            'assets': assets,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Get assets failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting AI-powered Bank Asset Agent on port {port}")
    logger.info(f"AI capabilities enabled: {ai_market_analyzer is not None}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
