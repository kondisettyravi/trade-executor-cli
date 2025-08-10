"""Orchestrator that wraps around the claude CLI command for 24/7 trading automation."""

import asyncio
import subprocess
import json
import time
import os
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import structlog
import re

logger = structlog.get_logger(__name__)


class ClaudeOrchestrator:
    """24/7 trading orchestrator that uses the claude CLI command."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.is_running = False
        self.current_trade = None
        self.trade_history = []
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.monitoring_interval = self.config['trading']['monitoring_interval'] * 60  # Convert to seconds
        
    async def start_24_7_trading(self):
        """Start 24/7 automated trading using claude CLI."""
        logger.info("🚀 Starting 24/7 Claude Trading Orchestrator")
        self.is_running = True
        
        try:
            while self.is_running:
                if not self.current_trade:
                    # No active trade - start a new one
                    await self._initiate_new_trade()
                else:
                    # Monitor existing trade
                    await self._monitor_current_trade()
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Trading orchestrator stopped by user")
        except Exception as e:
            logger.error("❌ Orchestrator error", error=str(e))
        finally:
            self.is_running = False
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = "config/claude_trader.yaml"
        
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return self._get_default_config()
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            logger.info("✅ Configuration loaded successfully", config_path=config_path)
            return config
            
        except Exception as e:
            logger.error("❌ Failed to load config, using defaults", error=str(e))
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'trading': {
                'style': 'aggressive',
                'coins': ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE'],
                'position_size': {'min': 5, 'max': 25},
                'monitoring_interval': 15
            },
            'styles': {
                'aggressive': {
                    'description': 'very aggressive and profitable trader who takes bold positions and maximizes profits',
                    'risk_tolerance': 'high',
                    'position_preference': 'larger positions for maximum profit'
                }
            },
            'advanced': {
                'custom_prompt': '',
                'additional_instructions': '',
                'completion_keywords': [
                    'trade completed', 'position closed', 'trade closed',
                    'final profit', 'final loss', 'trade finished', 'position exited'
                ]
            }
        }
    
    def _build_trading_prompt(self) -> str:
        """Build trading prompt based on configuration."""
        # Check for custom prompt first
        if self.config['advanced']['custom_prompt']:
            return self.config['advanced']['custom_prompt']
        
        # Get trading configuration
        trading_config = self.config['trading']
        style_config = self.config['styles'][trading_config['style']]
        
        # Build coin list
        coins = ', '.join(trading_config['coins'])
        
        # Build position size range
        pos_min = trading_config['position_size']['min']
        pos_max = trading_config['position_size']['max']
        
        # Build base prompt
        prompt = (
            f"I would like to use the bybit mcp server and take a profitable trade on the major crypto "
            f"currencies such as {coins}. I want the trade to be profitable and would "
            f"want to monitor the trade and set the stop loss such that we don't get losses. Monitor the "
            f"trade every {trading_config['monitoring_interval']} minutes. Be the boss. Take the right decision. "
            f"You know that you are a {style_config['description']}. "
            f"Your risk tolerance is {style_config['risk_tolerance']} and you prefer {style_config['position_preference']}. "
            f"Choose position size between {pos_min}-{pos_max}% of available balance."
        )
        
        # Add additional instructions if any
        if self.config['advanced']['additional_instructions']:
            prompt += f" {self.config['advanced']['additional_instructions']}"
        
        return prompt

    async def _initiate_new_trade(self):
        """Initiate a new trade using claude CLI."""
        logger.info("🎯 Initiating new trade with Claude", 
                   style=self.config['trading']['style'],
                   coins=self.config['trading']['coins'])
        
        # Build trading prompt based on configuration
        prompt = self._build_trading_prompt()
        
        try:
            # Execute claude command
            result = await self._execute_claude_command(prompt)
            
            if result and self._parse_trade_initiation(result):
                logger.info("✅ New trade initiated successfully")
                self.current_trade = {
                    "initiated_at": datetime.now(),
                    "last_monitored": datetime.now(),
                    "status": "active",
                    "claude_response": result
                }
            else:
                logger.warning("⚠️ Failed to initiate trade, will retry in next cycle")
                
        except Exception as e:
            logger.error("❌ Error initiating trade", error=str(e))
    
    async def _monitor_current_trade(self):
        """Monitor the current active trade."""
        if not self.current_trade:
            return
            
        logger.info("👁️ Monitoring current trade with Claude")
        
        try:
            # Monitor trade using claude
            result = await self._execute_claude_command("monitor the trade", continue_mode=True)
            
            if result:
                self.current_trade["last_monitored"] = datetime.now()
                self.current_trade["latest_status"] = result
                
                # Check if trade is completed
                if self._is_trade_completed(result):
                    logger.info("🎉 Trade completed successfully")
                    self._complete_current_trade(result)
                else:
                    logger.info("📊 Trade monitoring update received")
            else:
                logger.warning("⚠️ Failed to get monitoring update")
                
        except Exception as e:
            logger.error("❌ Error monitoring trade", error=str(e))
    
    async def _execute_claude_command(self, prompt: str, continue_mode: bool = False) -> Optional[str]:
        """Execute the claude CLI command."""
        try:
            # Build command
            if continue_mode:
                cmd = ["claude", "-p", "-c", prompt]
            else:
                cmd = ["claude", "-p", prompt]
            
            logger.info("🔧 Executing claude command", command=" ".join(cmd))
            
            # Set up environment variables for Claude
            env = {
                **dict(os.environ),  # Copy existing environment
                "ANTHROPIC_MODEL": "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "CLAUDE_CODE_USE_BEDROCK": "1",
                "AWS_PROFILE": "fintech-tax-bedrock-full-access-profile",
                "AWS_REGION": "us-west-2"
            }
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/Users/rkondis/personalwork/trade-executor-cli",
                env=env
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                result = stdout.decode('utf-8').strip()
                logger.info("✅ Claude command executed successfully", 
                          response_length=len(result))
                return result
            else:
                error_msg = stderr.decode('utf-8').strip()
                logger.error("❌ Claude command failed", 
                           return_code=process.returncode, 
                           error=error_msg)
                return None
                
        except Exception as e:
            logger.error("❌ Error executing claude command", error=str(e))
            return None
    
    def _parse_trade_initiation(self, response: str) -> bool:
        """Parse claude response to determine if trade was initiated."""
        if not response:
            return False
            
        # Look for indicators of successful trade initiation
        success_indicators = [
            "trade is now active",
            "position entry",
            "executed",
            "entry price",
            "stop loss",
            "take profit",
            "position size"
        ]
        
        response_lower = response.lower()
        found_indicators = sum(1 for indicator in success_indicators 
                             if indicator in response_lower)
        
        # Consider successful if we find multiple indicators
        success = found_indicators >= 3
        
        logger.info("📋 Trade initiation analysis", 
                   indicators_found=found_indicators,
                   success=success)
        
        return success
    
    def _is_trade_completed(self, response: str) -> bool:
        """Check if the trade has been completed based on claude response."""
        if not response:
            return False
            
        # Use configurable completion indicators
        completion_indicators = self.config['advanced']['completion_keywords']
        
        response_lower = response.lower()
        
        for indicator in completion_indicators:
            if indicator.lower() in response_lower:
                logger.info("🏁 Trade completion detected", indicator=indicator)
                return True
        
        return False
    
    def _complete_current_trade(self, final_response: str):
        """Complete the current trade and prepare for next one."""
        if self.current_trade:
            self.current_trade["completed_at"] = datetime.now()
            self.current_trade["final_response"] = final_response
            self.current_trade["status"] = "completed"
            
            # Add to history
            self.trade_history.append(self.current_trade.copy())
            
            # Clear current trade
            self.current_trade = None
            
            logger.info("📈 Trade completed and archived", 
                       total_trades=len(self.trade_history))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "is_running": self.is_running,
            "current_trade": self.current_trade,
            "total_trades": len(self.trade_history),
            "last_activity": datetime.now().isoformat(),
            "monitoring_interval_minutes": self.monitoring_interval // 60
        }
    
    def stop(self):
        """Stop the orchestrator."""
        logger.info("🛑 Stopping Claude orchestrator")
        self.is_running = False


# CLI interface for the orchestrator
async def main():
    """Main entry point for the orchestrator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Trading Orchestrator")
    parser.add_argument("--start", action="store_true", help="Start 24/7 trading")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--interval", type=int, default=15, help="Monitoring interval in minutes")
    
    args = parser.parse_args()
    
    orchestrator = ClaudeOrchestrator()
    
    if args.interval != 15:
        orchestrator.monitoring_interval = args.interval * 60
    
    if args.start:
        print("🚀 Starting 24/7 Claude Trading Orchestrator...")
        print(f"📊 Monitoring interval: {args.interval} minutes")
        print("Press Ctrl+C to stop")
        await orchestrator.start_24_7_trading()
    elif args.status:
        status = orchestrator.get_status()
        print(json.dumps(status, indent=2, default=str))
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
