"""Configuration management for Donetick MCP server."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration for Donetick MCP server."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.donetick_base_url = os.getenv("DONETICK_BASE_URL")
        self.donetick_api_token = os.getenv("DONETICK_API_TOKEN")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.rate_limit_per_second = float(os.getenv("RATE_LIMIT_PER_SECOND", "10.0"))
        self.rate_limit_burst = int(os.getenv("RATE_LIMIT_BURST", "10"))

        # Validate required configuration
        self._validate()

    def _validate(self):
        """Validate that required configuration is present."""
        if not self.donetick_base_url:
            raise ValueError(
                "DONETICK_BASE_URL environment variable is required. "
                "Please set it to your Donetick instance URL."
            )

        if not self.donetick_api_token:
            raise ValueError(
                "DONETICK_API_TOKEN environment variable is required. "
                "Please generate a token in Donetick Settings > Access Token."
            )

        # Normalize base URL (remove trailing slash)
        self.donetick_base_url = self.donetick_base_url.rstrip("/")

    def configure_logging(self):
        """Configure logging based on log level."""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Global configuration instance
config = Config()
