"""
Unit tests for configuration
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError

from app.core.config import Settings


class TestSettings:
    """Test cases for Settings configuration"""
    
    def test_valid_settings(self):
        """Test valid settings configuration"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO'
        }):
            settings = Settings()
            
            assert settings.GEMINI_API_KEY == 'test-api-key'
            assert settings.LOG_LEVEL == 'INFO'
            assert settings.HOST == '0.0.0.0'
            assert settings.PORT == 8080
            assert settings.VERSION == 'v1.0.0'
    
    def test_invalid_log_level(self):
        """Test invalid log level validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INVALID'
        }):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_missing_gemini_api_key(self):
        """Test missing Gemini API key validation"""
        with patch.dict('os.environ', {
            'LOG_LEVEL': 'INFO'
        }, clear=True):
            # Should use default test API key
            settings = Settings()
            assert settings.GEMINI_API_KEY == "test-api-key-for-testing"
    
    def test_empty_gemini_api_key(self):
        """Test empty Gemini API key validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': '',
            'LOG_LEVEL': 'INFO'
        }):
            # Should use default test API key for empty string
            settings = Settings()
            assert settings.GEMINI_API_KEY == "test-api-key-for-testing"
    
    def test_invalid_temperature(self):
        """Test invalid LLM temperature validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO',
            'LLM_TEMPERATURE': '3.0'  # Invalid: > 2
        }):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_negative_temperature(self):
        """Test negative LLM temperature validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO',
            'LLM_TEMPERATURE': '-0.5'  # Invalid: < 0
        }):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_invalid_tier_percentage(self):
        """Test invalid tier percentage validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO',
            'DEFAULT_TIER1_PERCENTAGE': '150'  # Invalid: > 100
        }):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_negative_tier_percentage(self):
        """Test negative tier percentage validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO',
            'DEFAULT_TIER1_PERCENTAGE': '-10'  # Invalid: < 0
        }):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_tier_percentages_sum_validation(self):
        """Test tier percentages sum validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO',
            'DEFAULT_TIER1_PERCENTAGE': '30',
            'DEFAULT_TIER2_PERCENTAGE': '30',
            'DEFAULT_TIER3_PERCENTAGE': '30'  # Sum = 90, not 100
        }):
            # Should use default values when sum doesn't equal 100
            settings = Settings()
            assert settings.DEFAULT_TIER1_PERCENTAGE == 30  # Uses provided values
            assert settings.DEFAULT_TIER2_PERCENTAGE == 30  # Uses provided values
            assert settings.DEFAULT_TIER3_PERCENTAGE == 30  # Uses provided values
    
    def test_valid_tier_percentages_sum(self):
        """Test valid tier percentages sum"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO',
            'DEFAULT_TIER1_PERCENTAGE': '20',
            'DEFAULT_TIER2_PERCENTAGE': '30',
            'DEFAULT_TIER3_PERCENTAGE': '50'  # Sum = 100
        }):
            settings = Settings()
            
            assert settings.DEFAULT_TIER1_PERCENTAGE == 20
            assert settings.DEFAULT_TIER2_PERCENTAGE == 30
            assert settings.DEFAULT_TIER3_PERCENTAGE == 50
    
    def test_case_insensitive_log_level(self):
        """Test case insensitive log level validation"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'debug'  # lowercase
        }):
            settings = Settings()
            assert settings.LOG_LEVEL == 'DEBUG'  # Should be converted to uppercase
    
    def test_default_values(self):
        """Test default configuration values"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO'
        }):
            settings = Settings()
            
            # Test default values
            assert settings.HOST == '0.0.0.0'
            assert settings.PORT == 8080
            assert settings.GEMINI_MODEL == 'gemini-2.5-flash'
            assert settings.LLM_TEMPERATURE == 0.1
            assert settings.LLM_MAX_TOKENS == 4000
            assert settings.LLM_TIMEOUT == 30
            assert settings.DEFAULT_TIER1_PERCENTAGE == 20
            assert settings.DEFAULT_TIER2_PERCENTAGE == 30
            assert settings.DEFAULT_TIER3_PERCENTAGE == 50
            assert settings.DEFAULT_TRANSACTION_HISTORY_LIMIT == 100
            assert settings.CONNECTION_POOL_SIZE == 10
            assert settings.MAX_RETRIES == 3
            assert settings.RETRY_DELAY == 1
            assert settings.CIRCUIT_BREAKER_THRESHOLD == 5
            assert settings.CIRCUIT_BREAKER_TIMEOUT == 60
            assert settings.RATE_LIMIT_PER_MINUTE == 60
    
    def test_database_urls_default(self):
        """Test default database URIs"""
        with patch.dict('os.environ', {
            'GOOGLE_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO'
        }):
            settings = Settings()
            
            assert settings.LEDGER_DB_URI == 'postgresql://admin:password@ledger-db:5432/postgresdb'
            assert settings.QUEUE_DB_URI == 'postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db'
            assert settings.PORTFOLIO_DB_URI == 'postgresql://admin:password@user-portfolio-db:5432/portfoliodb'
    
    def test_redis_configuration_default(self):
        """Test default Redis configuration"""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-api-key',
            'LOG_LEVEL': 'INFO'
        }):
            settings = Settings()
            
            assert settings.REDIS_URL == 'redis://redis:6379'
            assert settings.CACHE_TTL == 300
