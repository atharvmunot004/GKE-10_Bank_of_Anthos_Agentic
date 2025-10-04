"""
Configuration management for User Tier Agent
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"
    VERSION: str = "v1.0.0"
    ENVIRONMENT: str = "development"
    
    # LLM Configuration
    GEMINI_API_KEY: str = "test-api-key-for-testing"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4000
    LLM_TIMEOUT: int = 30
    
    # Database URLs
    LEDGER_DB_URL: str = "http://ledger-db:8080"
    QUEUE_DB_URL: str = "http://queue-db:8080"
    PORTFOLIO_DB_URL: str = "http://portfolio-db:8080"
    
    # Redis Configuration
    REDIS_URL: str = "redis://redis:6379"
    CACHE_TTL: int = 300
    
    # Default Allocations
    DEFAULT_TIER1_PERCENTAGE: int = 20
    DEFAULT_TIER2_PERCENTAGE: int = 30
    DEFAULT_TIER3_PERCENTAGE: int = 50
    DEFAULT_TRANSACTION_HISTORY_LIMIT: int = 100
    
    # Performance Configuration
    CONNECTION_POOL_SIZE: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 60
    
    # Security
    JWT_SECRET_KEY: Optional[str] = None
    RATE_LIMIT_PER_MINUTE: int = 60
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of {valid_levels}')
        return v.upper()
    
    @field_validator('GEMINI_API_KEY')
    @classmethod
    def validate_gemini_api_key(cls, v):
        if not v or v == "test-api-key-for-testing":
            return "test-api-key-for-testing"
        if len(v) < 10:
            raise ValueError('GEMINI_API_KEY must be at least 10 characters long')
        return v
    
    @field_validator('LLM_TEMPERATURE')
    @classmethod
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError('LLM_TEMPERATURE must be between 0 and 2')
        return v
    
    @field_validator('DEFAULT_TIER1_PERCENTAGE', 'DEFAULT_TIER2_PERCENTAGE', 'DEFAULT_TIER3_PERCENTAGE')
    @classmethod
    def validate_tier_percentages(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Tier percentages must be between 0 and 100')
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


# Global settings instance
settings = Settings()
