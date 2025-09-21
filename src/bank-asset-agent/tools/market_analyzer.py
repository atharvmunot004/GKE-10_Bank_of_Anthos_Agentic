#!/usr/bin/env python3
# Copyright 2024 Google LLC
# Bank Asset Agent - Market Analyzer

import requests
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """AI agent for market data analysis and trend prediction"""
    
    def __init__(self, market_reader_url: str = None):
        self.market_reader_url = market_reader_url or os.environ.get('MARKET_READER_URL', 'http://market-reader-svc:8080')
    
    def get_market_data(self, symbols: List[str], time_range: str = "1d") -> Dict:
        """Retrieve real-time market data for given symbols"""
        try:
            response = requests.get(
                f"{self.market_reader_url}/api/market-data",
                params={'symbols': ','.join(symbols), 'time_range': time_range},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get market data: {e}")
            raise Exception(f"Market data retrieval failed: {e}")
    
    def analyze_trends(self, market_data: Dict) -> Dict:
        """Analyze market trends and patterns"""
        try:
            trends = {}
            for symbol, data in market_data.get('prices', {}).items():
                price = data.get('price', 0)
                change = data.get('change', 0)
                change_percent = data.get('change_percent', 0)
                
                # Simple trend analysis
                if change_percent > 2:
                    trend = "strong_bullish"
                    confidence = min(0.9, 0.5 + abs(change_percent) / 10)
                elif change_percent > 0.5:
                    trend = "bullish"
                    confidence = min(0.8, 0.4 + abs(change_percent) / 20)
                elif change_percent < -2:
                    trend = "strong_bearish"
                    confidence = min(0.9, 0.5 + abs(change_percent) / 10)
                elif change_percent < -0.5:
                    trend = "bearish"
                    confidence = min(0.8, 0.4 + abs(change_percent) / 20)
                else:
                    trend = "neutral"
                    confidence = 0.3
                
                trends[symbol] = {
                    'trend': trend,
                    'confidence': confidence,
                    'price': price,
                    'change': change,
                    'change_percent': change_percent
                }
            
            return {
                'trends': trends,
                'overall_sentiment': self._calculate_overall_sentiment(trends),
                'analysis_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
            raise Exception(f"Trend analysis failed: {e}")
    
    def predict_prices(self, symbols: List[str], horizon: str = "1h") -> Dict:
        """Predict asset price movements"""
        try:
            # Get historical data for prediction
            market_data = self.get_market_data(symbols, "7d")
            trends = self.analyze_trends(market_data)
            
            predictions = {}
            for symbol in symbols:
                if symbol in trends['trends']:
                    trend_data = trends['trends'][symbol]
                    current_price = trend_data['price']
                    trend = trend_data['trend']
                    confidence = trend_data['confidence']
                    
                    # Simple price prediction based on trend
                    if trend in ['strong_bullish', 'bullish']:
                        predicted_change = 0.01 * confidence * (2 if trend == 'strong_bullish' else 1)
                    elif trend in ['strong_bearish', 'bearish']:
                        predicted_change = -0.01 * confidence * (2 if trend == 'strong_bearish' else 1)
                    else:
                        predicted_change = 0
                    
                    predicted_price = current_price * (1 + predicted_change)
                    
                    predictions[symbol] = {
                        'current_price': current_price,
                        'predicted_price': predicted_price,
                        'predicted_change': predicted_change,
                        'confidence': confidence,
                        'trend': trend,
                        'horizon': horizon
                    }
            
            return {
                'predictions': predictions,
                'prediction_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to predict prices: {e}")
            raise Exception(f"Price prediction failed: {e}")
    
    def _calculate_overall_sentiment(self, trends: Dict) -> str:
        """Calculate overall market sentiment"""
        if not trends:
            return "neutral"
        
        bullish_count = sum(1 for t in trends.values() if t['trend'] in ['bullish', 'strong_bullish'])
        bearish_count = sum(1 for t in trends.values() if t['trend'] in ['bearish', 'strong_bearish'])
        total_count = len(trends)
        
        if bullish_count > total_count * 0.6:
            return "bullish"
        elif bearish_count > total_count * 0.6:
            return "bearish"
        else:
            return "neutral"
    
    def get_market_summary(self, symbols: List[str]) -> Dict:
        """Get comprehensive market summary"""
        try:
            market_data = self.get_market_data(symbols)
            trends = self.analyze_trends(market_data)
            predictions = self.predict_prices(symbols)
            
            return {
                'market_data': market_data,
                'trends': trends,
                'predictions': predictions,
                'summary_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get market summary: {e}")
            raise Exception(f"Market summary failed: {e}")
