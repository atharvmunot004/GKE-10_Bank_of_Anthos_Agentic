"""
Configuration management for user-request-queue-svc
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "user-request-queue-svc"
    service_port: int = 8080
    log_level: str = "INFO"
    
    # Database configuration
    queue_db_uri: str = "postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db"
    queue_db_host: str = "queue-db"
    queue_db_port: int = 5432
    queue_db_name: str = "queue-db"
    queue_db_user: str = "queue-admin"
    queue_db_password: str = "queue-pwd"
    
    # External service configuration
    bank_asset_agent_url: str = "http://bank-asset-agent:8080/api/v1/process-portfolio"
    bank_asset_agent_timeout: int = 30
    bank_asset_agent_retry_attempts: int = 3
    bank_asset_agent_retry_delay: int = 1
    
    # Queue processing configuration
    polling_interval: int = 5
    batch_size: int = 10
    max_retries: int = 3
    retry_delay: int = 1
    
    # Database connection pool
    connection_pool_size: int = 10
    max_overflow: int = 20
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
