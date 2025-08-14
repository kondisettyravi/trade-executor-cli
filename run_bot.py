#!/usr/bin/env python3
"""
Trading Bot Launcher - Simple script to start the trading bot
"""
import asyncio
import sys
import logging
from main import TradingBot

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

async def main():
    """Main launcher function"""
    print("🚀 Starting Crypto Trading Bot")
    print("=" * 50)
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create and run the trading bot
        bot = TradingBot()
        
        logger.info("Trading bot initialized successfully")
        logger.info("Starting main trading loop...")
        
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Trading bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
