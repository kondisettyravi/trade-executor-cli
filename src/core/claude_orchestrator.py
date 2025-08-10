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

# Import trade auditor
try:
    from ..web.dashboard import TradeAuditor, create_dashboard
except ImportError:
    # Fallback if web dependencies not available
    TradeAuditor = None
    create_dashboard = None


class ClaudeOrchestrator:
    """24/7 trading orchestrator that uses the claude CLI command."""
    
    def __init__(self, config_path: Optional[str] = None, enable_web_dashboard: bool = True):
        self.is_running = False
        self.current_trade = None
        self.trade_history = []
        self.current_trade_id = None
        self.state_file = "data/orchestrator_state.json"
        
        # Load configuration
        self.config = self._load_config(config_path)
        self.monitoring_interval = self.config['trading']['monitoring_interval'] * 60  # Convert to seconds
        
        # Initialize trade auditor and web dashboard
        self.auditor = None
        self.dashboard = None
        if enable_web_dashboard and TradeAuditor:
            try:
                self.auditor = TradeAuditor()
                self.dashboard = create_dashboard()
                logger.info("✅ Trade auditor and web dashboard initialized")
            except Exception as e:
                logger.warning("⚠️ Failed to initialize web dashboard", error=str(e))
        
        # Load previous state if exists
        self._load_state()
        
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
                
                # Save state after each cycle
                self._save_state()
                
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
        
        # Build base prompt with aggressive 20% daily target
        prompt = (
            f"I would like to use the bybit mcp server and take a profitable trade on the major crypto "
            f"currencies such as {coins}. TARGET: 20% DAILY RETURNS on total wallet value. "
            f"Use UNLIMITED LEVERAGE as needed to achieve this target. Be extremely aggressive and profitable. "
            f"Monitor the trade every {trading_config['monitoring_interval']} minutes. Be the boss. Take the right decision. "
            f"You know that you are a {style_config['description']}. "
            f"Your risk tolerance is {style_config['risk_tolerance']} and you prefer {style_config['position_preference']}. "
            f"GOAL: {style_config.get('daily_target', '20% daily returns')}. "
            f"LEVERAGE: {style_config.get('leverage_usage', 'Use maximum leverage as needed')}. "
            f"Position size: Use whatever size and leverage needed to achieve 20% daily profit target."
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
                initiated_at = datetime.now()
                self.current_trade = {
                    "initiated_at": initiated_at,
                    "last_monitored": initiated_at,
                    "status": "active",
                    "claude_response": result
                }
                
                # Log to auditor
                if self.auditor:
                    trade_data = {
                        "style": self.config['trading']['style'],
                        "coins": self.config['trading']['coins'],
                        "initiated_at": initiated_at,
                        "prompt": prompt,
                        "claude_response": result
                    }
                    self.current_trade_id = self.auditor.log_trade_initiation(trade_data)
                    logger.info("📊 Trade logged to audit system", trade_id=self.current_trade_id)
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
            # Enhanced monitoring prompt with 20% daily target emphasis and clear execution instructions
            monitoring_prompt = (
                "Monitor the current trade and provide a detailed update. REMEMBER: TARGET is 20% DAILY RETURNS on total wallet value. "
                "Use unlimited leverage as needed. IMPORTANT: If you decide to close the position, USE THE BYBIT MCP to actually execute the close order - don't just say 'preparing to close'. "
                "Please include: "
                "1) Current position status (which coin, profit/loss, leverage used) "
                "2) Progress toward 20% daily target - are we on track? "
                "3) Your decision (hold, close, adjust leverage, add positions) and why "
                "4) If closing: EXECUTE the close order using Bybit MCP and confirm closure "
                "5) Market analysis that influenced your decision "
                "6) Next steps to achieve 20% daily profit target. "
                "Be extremely aggressive and profit-focused. Use maximum leverage if needed to hit the 20% daily target. "
                "EXECUTE ACTIONS, don't just prepare or plan - use the MCP tools to actually trade."
            )
            
            # Monitor trade using claude
            result = await self._execute_claude_command(monitoring_prompt, continue_mode=True)
            
            if result:
                self.current_trade["last_monitored"] = datetime.now()
                self.current_trade["latest_status"] = result
                
                # Extract key information from Claude's response
                trade_analysis = self._extract_trade_analysis(result)
                
                # Log monitoring update to auditor
                if self.auditor and self.current_trade_id:
                    update_data = {
                        "timestamp": datetime.now(),
                        "claude_response": result,
                        "analysis": trade_analysis["summary"]
                    }
                    self.auditor.log_trade_update(self.current_trade_id, update_data)
                
                # Enhanced logging with trade details
                logger.info("📊 Trade monitoring update", 
                          trade_status=trade_analysis["status"],
                          current_position=trade_analysis["position"],
                          decision=trade_analysis["decision"],
                          reasoning=trade_analysis["reasoning"][:100] + "..." if len(trade_analysis["reasoning"]) > 100 else trade_analysis["reasoning"])
                
                # Check if trade is completed
                if self._is_trade_completed(result):
                    completion_reason = self._extract_completion_reason(result)
                    logger.info("🎉 Trade completed successfully", 
                              completion_reason=completion_reason,
                              final_decision=trade_analysis["decision"])
                    self._complete_current_trade(result)
                else:
                    logger.info("🔄 Trade continues - monitoring next cycle", 
                              next_action=trade_analysis["next_action"])
            else:
                logger.warning("⚠️ Failed to get monitoring update")
                
        except Exception as e:
            logger.error("❌ Error monitoring trade", error=str(e))
    
    async def _execute_claude_command(self, prompt: str, continue_mode: bool = False) -> Optional[str]:
        """Execute the claude CLI command with dangerous skip permissions for uninterrupted operation."""
        try:
            # Build command with --dangerously-skip-permissions for uninterrupted execution
            if continue_mode:
                cmd = ["claude", "--dangerously-skip-permissions", "-p", "-c", prompt]
            else:
                cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]
            
            logger.info("🔧 Executing claude command (uninterrupted mode)", command=" ".join(cmd))
            
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
            completed_at = datetime.now()
            self.current_trade["completed_at"] = completed_at
            self.current_trade["final_response"] = final_response
            self.current_trade["status"] = "completed"
            
            # Log completion to auditor
            if self.auditor and self.current_trade_id:
                completion_data = {
                    "completed_at": completed_at,
                    "final_response": final_response,
                    "completion_reason": self._extract_completion_reason(final_response)
                }
                self.auditor.log_trade_completion(self.current_trade_id, completion_data)
                logger.info("📊 Trade completion logged to audit system", trade_id=self.current_trade_id)
            
            # Add to history
            self.trade_history.append(self.current_trade.copy())
            
            # Clear current trade
            self.current_trade = None
            self.current_trade_id = None
            
            logger.info("📈 Trade completed and archived", 
                       total_trades=len(self.trade_history))
    
    def _extract_trade_analysis(self, response: str) -> Dict[str, str]:
        """Extract key trading information from Claude's response."""
        if not response:
            return {
                "status": "Unknown",
                "position": "Unknown",
                "decision": "No response",
                "reasoning": "No response received",
                "next_action": "Continue monitoring",
                "summary": "No analysis available"
            }
        
        response_lower = response.lower()
        
        # Extract current position/trade status
        position = "Unknown"
        if "btc" in response_lower or "bitcoin" in response_lower:
            position = "BTC position"
        elif "eth" in response_lower or "ethereum" in response_lower:
            position = "ETH position"
        elif "sol" in response_lower or "solana" in response_lower:
            position = "SOL position"
        elif "xrp" in response_lower or "ripple" in response_lower:
            position = "XRP position"
        elif "doge" in response_lower or "dogecoin" in response_lower:
            position = "DOGE position"
        
        # Extract trade status
        status = "Active"
        if "profit" in response_lower:
            status = "In profit"
        elif "loss" in response_lower:
            status = "In loss"
        elif "break" in response_lower and "even" in response_lower:
            status = "Break even"
        
        # Extract decision
        decision = "Continue holding"
        if "close" in response_lower or "exit" in response_lower:
            decision = "Closing position"
        elif "hold" in response_lower or "maintain" in response_lower:
            decision = "Holding position"
        elif "adjust" in response_lower or "modify" in response_lower:
            decision = "Adjusting position"
        elif "monitor" in response_lower:
            decision = "Monitoring closely"
        
        # Extract reasoning (first sentence or key phrase)
        reasoning = "Continuing trade monitoring"
        sentences = response.split('.')
        if sentences:
            # Find the most informative sentence
            for sentence in sentences[:3]:  # Check first 3 sentences
                sentence = sentence.strip()
                if any(keyword in sentence.lower() for keyword in ['because', 'due to', 'since', 'as', 'given']):
                    reasoning = sentence
                    break
                elif any(keyword in sentence.lower() for keyword in ['profit', 'loss', 'price', 'market', 'trend']):
                    reasoning = sentence
                    break
            
            if reasoning == "Continuing trade monitoring" and sentences[0]:
                reasoning = sentences[0].strip()
        
        # Extract next action
        next_action = "Continue monitoring"
        if "close" in response_lower:
            next_action = "Prepare to close"
        elif "watch" in response_lower or "monitor" in response_lower:
            next_action = "Continue monitoring"
        elif "adjust" in response_lower:
            next_action = "Adjust parameters"
        
        # Create summary
        summary = f"{status} - {decision}: {reasoning[:50]}..."
        
        return {
            "status": status,
            "position": position,
            "decision": decision,
            "reasoning": reasoning,
            "next_action": next_action,
            "summary": summary
        }
    
    def _extract_completion_reason(self, response: str) -> str:
        """Extract the reason for trade completion from Claude's response."""
        if not response:
            return "Unknown reason"
        
        # Look for common completion patterns
        response_lower = response.lower()
        
        if "profit" in response_lower and "target" in response_lower:
            return "Profit target reached"
        elif "stop loss" in response_lower or "stop-loss" in response_lower:
            return "Stop loss triggered"
        elif "market condition" in response_lower:
            return "Market conditions changed"
        elif "risk" in response_lower:
            return "Risk management decision"
        elif "time" in response_lower and ("exit" in response_lower or "close" in response_lower):
            return "Time-based exit"
        else:
            return "Trade completion decision"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "is_running": self.is_running,
            "current_trade": self.current_trade,
            "total_trades": len(self.trade_history),
            "last_activity": datetime.now().isoformat(),
            "monitoring_interval_minutes": self.monitoring_interval // 60
        }
    
    def _load_state(self):
        """Load previous orchestrator state from file."""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                # Restore current trade if it exists
                if state.get("current_trade"):
                    # Convert datetime strings back to datetime objects
                    trade = state["current_trade"]
                    if trade.get("initiated_at"):
                        trade["initiated_at"] = datetime.fromisoformat(trade["initiated_at"])
                    if trade.get("last_monitored"):
                        trade["last_monitored"] = datetime.fromisoformat(trade["last_monitored"])
                    if trade.get("completed_at"):
                        trade["completed_at"] = datetime.fromisoformat(trade["completed_at"])
                    
                    self.current_trade = trade
                    self.current_trade_id = state.get("current_trade_id")
                    
                    logger.info("🔄 Resumed active trade from previous session", 
                              trade_id=self.current_trade_id,
                              initiated_at=self.current_trade["initiated_at"],
                              status=self.current_trade["status"])
                
                # Restore trade history
                if state.get("trade_history"):
                    for trade in state["trade_history"]:
                        # Convert datetime strings back to datetime objects
                        if trade.get("initiated_at"):
                            trade["initiated_at"] = datetime.fromisoformat(trade["initiated_at"])
                        if trade.get("last_monitored"):
                            trade["last_monitored"] = datetime.fromisoformat(trade["last_monitored"])
                        if trade.get("completed_at"):
                            trade["completed_at"] = datetime.fromisoformat(trade["completed_at"])
                    
                    self.trade_history = state["trade_history"]
                    logger.info("📚 Restored trade history", total_trades=len(self.trade_history))
                
                logger.info("✅ State restored successfully from previous session")
            else:
                logger.info("🆕 Starting fresh - no previous state found")
                
        except Exception as e:
            logger.error("❌ Failed to load previous state", error=str(e))
            logger.info("🆕 Starting fresh due to state loading error")
    
    def _save_state(self):
        """Save current orchestrator state to file."""
        try:
            # Ensure data directory exists
            Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare state data
            state = {
                "current_trade": None,
                "current_trade_id": self.current_trade_id,
                "trade_history": [],
                "last_saved": datetime.now().isoformat()
            }
            
            # Save current trade if exists
            if self.current_trade:
                trade = self.current_trade.copy()
                # Convert datetime objects to strings for JSON serialization
                if trade.get("initiated_at"):
                    trade["initiated_at"] = trade["initiated_at"].isoformat()
                if trade.get("last_monitored"):
                    trade["last_monitored"] = trade["last_monitored"].isoformat()
                if trade.get("completed_at"):
                    trade["completed_at"] = trade["completed_at"].isoformat()
                
                state["current_trade"] = trade
            
            # Save trade history
            for trade in self.trade_history:
                trade_copy = trade.copy()
                # Convert datetime objects to strings
                if trade_copy.get("initiated_at"):
                    trade_copy["initiated_at"] = trade_copy["initiated_at"].isoformat()
                if trade_copy.get("last_monitored"):
                    trade_copy["last_monitored"] = trade_copy["last_monitored"].isoformat()
                if trade_copy.get("completed_at"):
                    trade_copy["completed_at"] = trade_copy["completed_at"].isoformat()
                
                state["trade_history"].append(trade_copy)
            
            # Write state to file
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            logger.debug("💾 State saved successfully")
            
        except Exception as e:
            logger.error("❌ Failed to save state", error=str(e))
    
    def stop(self):
        """Stop the orchestrator and save state."""
        logger.info("🛑 Stopping Claude orchestrator")
        self.is_running = False
        
        # Save current state before stopping
        self._save_state()
        logger.info("💾 State saved for next session")


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
