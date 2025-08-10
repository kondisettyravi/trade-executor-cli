"""Configuration management for the trading CLI."""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TradingConfig(BaseSettings):
    """Trading-specific configuration."""
    position_sizes: List[int] = [5, 10, 15, 20, 25]
    max_daily_loss_percent: float = 10.0
    max_position_loss_percent: float = 5.0
    emergency_stop_loss_percent: float = 15.0
    price_check_interval_minutes: int = 15
    news_check_interval_minutes: int = 60
    allowed_pairs: List[str] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]
    max_trades_per_day: int = 3
    cooldown_between_trades_minutes: int = 30


class BedrockConfig(BaseSettings):
    """AWS Bedrock configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Bedrock configuration (can be overridden by environment variables)
    region: str = Field(default_factory=lambda: os.getenv("BEDROCK_REGION", "us-east-1"))
    model_id: str = Field(default_factory=lambda: os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0"))
    fallback_model_id: str = Field(default_factory=lambda: os.getenv("BEDROCK_FALLBACK_MODEL_ID", "us.anthropic.claude-3-haiku-20241022-v1:0"))
    max_tokens: int = 4000
    temperature: float = 0.1
    
    # AWS credentials (from environment or AWS profile)
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_session_token: Optional[str] = Field(None, env="AWS_SESSION_TOKEN")
    aws_profile: Optional[str] = Field(None, env="AWS_PROFILE")
    
    # New Bedrock API key authentication (recommended for development)
    bedrock_api_key: Optional[str] = Field(None, env="AWS_BEARER_TOKEN_BEDROCK")
    use_api_key: bool = False  # Set to True to use API key instead of AWS credentials


class BybitConfig(BaseSettings):
    """Bybit exchange configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Trading configuration (can be overridden by environment variables)
    testnet: bool = Field(default_factory=lambda: os.getenv("BYBIT_TESTNET", "false").lower() == "true")
    category: str = Field(default_factory=lambda: os.getenv("BYBIT_CATEGORY", "spot"))
    demo_mode: bool = Field(default_factory=lambda: os.getenv("BYBIT_DEMO_MODE", "true").lower() == "true")
    
    # API credentials (from environment)
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("BYBIT_API_KEY"))
    api_secret: Optional[str] = Field(default_factory=lambda: os.getenv("BYBIT_API_SECRET"))


class NewsSource(BaseSettings):
    """News source configuration."""
    name: str
    enabled: bool = True
    weight: float = 0.25


class NewsConfig(BaseSettings):
    """News aggregation configuration."""
    sources: List[Dict[str, Any]] = [
        {"name": "coindesk", "enabled": True, "weight": 0.3},
        {"name": "cryptocompare", "enabled": True, "weight": 0.25},
        {"name": "fear_greed_index", "enabled": True, "weight": 0.2},
        {"name": "social_sentiment", "enabled": True, "weight": 0.25}
    ]


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/trading.log"
    max_file_size_mb: int = 10
    backup_count: int = 5


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    path: str = "data/trades.db"
    backup_interval_hours: int = 24


class AppConfig(BaseSettings):
    """Main application configuration."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    trading: TradingConfig = TradingConfig()
    bedrock: BedrockConfig = BedrockConfig()
    bybit: BybitConfig = BybitConfig()
    news: NewsConfig = NewsConfig()
    logging: LoggingConfig = LoggingConfig()
    database: DatabaseConfig = DatabaseConfig()


class ConfigManager:
    """Configuration manager for loading and managing app settings."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/settings.yaml"
        self.config = self._load_config()
    
    def _load_config(self) -> AppConfig:
        """Load configuration from YAML file and environment variables."""
        config_data = {}
        
        # Load from YAML file if it exists
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Create nested config objects
        config = AppConfig()
        
        if 'trading' in config_data:
            config.trading = TradingConfig(**config_data['trading'])
        
        if 'bedrock' in config_data:
            config.bedrock = BedrockConfig(**config_data['bedrock'])
        
        if 'bybit' in config_data:
            config.bybit = BybitConfig(**config_data['bybit'])
        
        if 'news' in config_data:
            config.news = NewsConfig(**config_data['news'])
        
        if 'logging' in config_data:
            config.logging = LoggingConfig(**config_data['logging'])
        
        if 'database' in config_data:
            config.database = DatabaseConfig(**config_data['database'])
        
        return config
    
    def get_trading_config(self) -> TradingConfig:
        """Get trading configuration."""
        return self.config.trading
    
    def get_bedrock_config(self) -> BedrockConfig:
        """Get AWS Bedrock configuration."""
        return self.config.bedrock
    
    def get_bybit_config(self) -> BybitConfig:
        """Get Bybit configuration."""
        return self.config.bybit
    
    def get_news_config(self) -> NewsConfig:
        """Get news configuration."""
        return self.config.news
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.config.logging
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.config.database
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Check Bybit credentials
        if not self.config.bybit.api_key:
            errors.append("BYBIT_API_KEY environment variable is required")
        
        if not self.config.bybit.api_secret:
            errors.append("BYBIT_API_SECRET environment variable is required")
        
        # Check AWS/Bedrock credentials
        bedrock_config = self.config.bedrock
        if bedrock_config.use_api_key:
            # Using Bedrock API key authentication
            if not bedrock_config.bedrock_api_key:
                errors.append("AWS_BEARER_TOKEN_BEDROCK environment variable is required when use_api_key is true")
        else:
            # Using traditional AWS credentials
            if not bedrock_config.aws_profile and not bedrock_config.aws_access_key_id:
                errors.append("AWS credentials required: set AWS_PROFILE or AWS_ACCESS_KEY_ID, or use Bedrock API key")
        
        # Validate trading parameters
        trading_config = self.config.trading
        if trading_config.max_daily_loss_percent <= 0:
            errors.append("max_daily_loss_percent must be positive")
        
        if trading_config.max_position_loss_percent <= 0:
            errors.append("max_position_loss_percent must be positive")
        
        if not trading_config.allowed_pairs:
            errors.append("At least one trading pair must be specified")
        
        return errors


# Global config instance
config_manager = ConfigManager()
