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
    
    def __init__(self, config_path: Optional[str] = None, enable_web_dashboard: bool = True, 
                 session_name: Optional[str] = None, session_config: Optional[Dict[str, Any]] = None):
        self.is_running = False
        self.current_trade = None
        self.trade_history = []
        self.current_trade_id = None
        self.session_name = session_name or "default"
        self.state_file = f"data/orchestrator_state_{self.session_name}.json"
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.interaction_count = 0
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Apply session-specific overrides
        if session_config:
            self._apply_session_config(session_config)
        
        self.monitoring_interval = self.config['trading']['monitoring_interval'] * 60  # Convert to seconds
        
        # Initialize trade auditor and web dashboard with session-specific database
        self.auditor = None
        self.dashboard = None
        if enable_web_dashboard and TradeAuditor:
            try:
                db_path = f"data/trades_{self.session_name}.db"
                self.auditor = TradeAuditor(db_path)
                dashboard_port = 5000 + hash(self.session_name) % 1000  # Unique port per session
                self.dashboard = create_dashboard(db_path, dashboard_port)
                logger.info("✅ Trade auditor and web dashboard initialized", 
                          session=self.session_name, db_path=db_path, port=dashboard_port)
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
    
    def _apply_session_config(self, session_config: Dict[str, Any]):
        """Apply session-specific configuration overrides."""
        if 'coins' in session_config:
            self.config['trading']['coins'] = session_config['coins']
            logger.info("📝 Session coins override applied", coins=session_config['coins'])
        
        if 'style' in session_config:
            if session_config['style'] in self.config['styles']:
                self.config['trading']['style'] = session_config['style']
                logger.info("📝 Session style override applied", style=session_config['style'])
        
        if 'interval' in session_config:
            self.config['trading']['monitoring_interval'] = session_config['interval']
            logger.info("📝 Session interval override applied", interval=session_config['interval'])
        
        if 'port_offset' in session_config:
            # This will be used by the dashboard initialization
            pass
    
    def _build_trading_prompt(self) -> str:
        """Build trading prompt based on configuration."""
        # Check for custom prompt first
        if self.config['advanced']['custom_prompt']:
            return self.config['advanced']['custom_prompt']
        
        # Get trading configuration
        trading_config = self.config['trading']
        style_config = self.config['styles'][trading_config['style']]
        
        # Build coin list - use trending coins if none specified
        if trading_config['coins'] and trading_config['coins'] != ['AUTO']:
            coins = ', '.join(trading_config['coins'])
            coin_strategy = f"Focus on these specific coins: {coins}"
        else:
            coins = "trending cryptocurrencies"
            coin_strategy = "DYNAMIC COIN SELECTION: Use the get_trending_coins MCP tool to identify the TOP TRENDING coins with highest volume, volatility, and momentum. Select the most profitable opportunities from the trending coins list."
        
        # Build position size range
        pos_min = trading_config['position_size']['min']
        pos_max = trading_config['position_size']['max']
        
        # Build analytical, data-driven prompt with futures market specification and advanced MCP tools
        prompt = (
            f"🎯 PRIMARY OBJECTIVE: ACHIEVE 20% DAILY RETURNS ON TOTAL WALLET VALUE 🎯\n\n"
            f"Please analyze the cryptocurrency FUTURES market using the bybit mcp server and execute a data-driven "
            f"FUTURES trade on {coins} based on comprehensive market analysis. "
            f"MARKET: Use Bybit FUTURES (linear perpetual contracts) for leverage trading. "
            f"TARGET: 20% DAILY PROFIT using HIGH LEVERAGE (10x-100x) to amplify returns. "
            f"LEVERAGE STRATEGY: Use significant leverage (minimum 10x, up to 100x) to achieve the 20% daily target. "
            f"\n\nCOIN SELECTION STRATEGY: {coin_strategy}"
            f"\n\nAdvanced Analysis Framework (Use ALL available MCP tools):"
            f"\n1. VOLUME PROFILE ANALYSIS: Use volume profile tool to identify Point of Control (POC) and Value Area for key support/resistance levels"
            f"\n2. MARKET CORRELATION: Analyze BTC-ETH correlation and volatility ratios to understand market relationships"
            f"\n3. MULTI-TIMEFRAME MOMENTUM: Use momentum scanner across multiple timeframes for trend confirmation"
            f"\n4. FUTURES MARKET DATA: Examine perpetual contract price action, funding rates, open interest"
            f"\n5. TECHNICAL INDICATORS: Analyze RSI, MACD, moving averages, support/resistance levels"
            f"\n6. ON-CHAIN METRICS: If available, analyze network health and whale activity for fundamental insights"
            f"\n7. RISK ASSESSMENT: Evaluate market conditions, liquidity, and leverage risks using correlation data"
            f"\n8. POSITION SIZING: Calculate optimal position size with leverage based on volatility analysis"
            f"\n9. ENTRY/EXIT STRATEGY: Use POC and Value Area levels for precise entry points, stop-loss, and take-profit"
            f"\n\nFutures Trading Parameters:"
            f"\n- Market Type: Linear Perpetual Futures (USDT margin)"
            f"\n- Risk Profile: {style_config['risk_tolerance']} risk tolerance"
            f"\n- Position Preference: {style_config['position_preference']}"
            f"\n- Monitoring Frequency: Every {trading_config['monitoring_interval']} minutes"
            f"\n- Leverage: Use appropriate leverage based on volatility analysis and correlation data"
            f"\n\nDecision Criteria: Base all futures trading decisions on comprehensive analysis using volume profile, "
            f"correlation analysis, momentum scanning, and traditional technical indicators. Use POC levels for entries, "
            f"Value Area boundaries for risk management, and correlation data for position sizing."
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
                # Extract detailed trade information from Claude's response
                trade_details = self._extract_trade_initiation_details(result)
                
                logger.info("✅ New trade initiated successfully",
                          coin=trade_details["coin"],
                          side=trade_details["side"],
                          entry_price=trade_details["entry_price"],
                          position_size=trade_details["position_size"],
                          leverage=trade_details["leverage"],
                          stop_loss=trade_details["stop_loss"],
                          take_profit=trade_details["take_profit"])
                
                initiated_at = datetime.now()
                self.current_trade = {
                    "initiated_at": initiated_at,
                    "last_monitored": initiated_at,
                    "status": "active",
                    "claude_response": result,
                    "trade_details": trade_details
                }
                
                # Log to auditor
                if self.auditor:
                    trade_data = {
                        "style": self.config['trading']['style'],
                        "coins": self.config['trading']['coins'],
                        "initiated_at": initiated_at,
                        "prompt": prompt,
                        "claude_response": result,
                        "trade_details": trade_details
                    }
                    self.current_trade_id = self.auditor.log_trade_initiation(trade_data)
                    logger.info("📊 Trade logged to audit system", 
                              trade_id=self.current_trade_id,
                              coin=trade_details["coin"],
                              entry_price=trade_details["entry_price"])
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
            # Enhanced monitoring prompt with position isolation and fee considerations
            monitoring_prompt = (
                f"Monitor ONLY the specific position you created in this session (Trade ID: {self.current_trade_id}). "
                f"IGNORE any other positions on the account. "
                f"Quick status check using Bybit MCP: "
                f"1) Current P&L and price for YOUR position only (INCLUDE exchange fees) "
                f"2) Decision: hold, close, or ADJUST TP/SL levels for YOUR position "
                f"3) If profitable: TIGHTEN stop-loss to protect NET profits after fees, adjust TP higher "
                f"4) If losing: consider reducing SL closer to break-even (account for fees) "
                f"5) Fee consideration: Factor in trading fees (maker/taker) for all decisions "
                f"6) Brief reason (1-2 sentences) "
                f"Execute any adjustments or closures immediately via MCP for YOUR position only. Keep response concise."
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
    
    def _calculate_token_cost(self, input_tokens: int, output_tokens: int, model: str = "claude-3.5-sonnet") -> float:
        """Calculate the cost of Claude API usage based on token counts."""
        # Claude 3.5 Sonnet pricing (as of 2024)
        pricing = {
            "claude-3.5-sonnet": {
                "input": 0.003,   # $0.003 per 1K input tokens
                "output": 0.015   # $0.015 per 1K output tokens
            },
            "claude-3-haiku": {
                "input": 0.00025, # $0.00025 per 1K input tokens
                "output": 0.00125 # $0.00125 per 1K output tokens
            },
            "claude-3-opus": {
                "input": 0.015,   # $0.015 per 1K input tokens
                "output": 0.075   # $0.075 per 1K output tokens
            }
        }
        
        # Default to Sonnet pricing if model not found
        rates = pricing.get(model, pricing["claude-3.5-sonnet"])
        
        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]
        
        return input_cost + output_cost
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Rough estimation: ~4 characters per token for English text
        return len(text) // 4
    
    def _analyze_claude_error(self, stderr: str, stdout: str, return_code: int) -> Dict[str, str]:
        """Analyze Claude command errors and provide detailed diagnostics."""
        error_type = "Unknown Error"
        description = "An unknown error occurred"
        suggested_fix = "Check Claude CLI installation and configuration"
        
        # Combine stderr and stdout for analysis
        full_error = f"{stderr} {stdout}".lower()
        
        # Authentication/API Key errors
        if any(keyword in full_error for keyword in ["authentication", "api key", "unauthorized", "invalid key", "forbidden"]):
            error_type = "Authentication Error"
            description = "Claude CLI authentication failed - invalid or missing API key"
            suggested_fix = "Check ANTHROPIC_API_KEY environment variable or AWS Bedrock credentials"
        
        # AWS/Bedrock specific errors
        elif any(keyword in full_error for keyword in ["bedrock", "aws", "credentials", "access denied", "region"]):
            error_type = "AWS Bedrock Error"
            description = "AWS Bedrock access failed - credentials or region issue"
            suggested_fix = "Verify AWS_PROFILE, AWS_REGION, and Bedrock permissions"
        
        # Network/Connection errors
        elif any(keyword in full_error for keyword in ["network", "connection", "timeout", "unreachable", "dns"]):
            error_type = "Network Error"
            description = "Network connectivity issue - cannot reach Claude API"
            suggested_fix = "Check internet connection and firewall settings"
        
        # Rate limiting errors
        elif any(keyword in full_error for keyword in ["rate limit", "too many requests", "quota", "throttle"]):
            error_type = "Rate Limit Error"
            description = "API rate limit exceeded - too many requests"
            suggested_fix = "Reduce monitoring frequency or wait before retrying"
        
        # Model/Service errors
        elif any(keyword in full_error for keyword in ["model", "service unavailable", "internal error", "server error"]):
            error_type = "Service Error"
            description = "Claude service or model unavailable"
            suggested_fix = "Wait and retry - service may be temporarily unavailable"
        
        # Command not found
        elif any(keyword in full_error for keyword in ["command not found", "no such file", "not found"]):
            error_type = "Command Not Found"
            description = "Claude CLI command not found in PATH"
            suggested_fix = "Install Claude CLI or add it to your PATH environment variable"
        
        # Permission errors
        elif any(keyword in full_error for keyword in ["permission denied", "access denied", "not permitted"]):
            error_type = "Permission Error"
            description = "Permission denied - insufficient access rights"
            suggested_fix = "Check file permissions and user access rights"
        
        # MCP Server errors
        elif any(keyword in full_error for keyword in ["mcp", "server", "bybit", "connection refused"]):
            error_type = "MCP Server Error"
            description = "MCP server (Bybit) connection failed"
            suggested_fix = "Ensure Bybit MCP server is running and accessible"
        
        # Timeout errors
        elif any(keyword in full_error for keyword in ["timeout", "timed out", "deadline exceeded"]):
            error_type = "Timeout Error"
            description = "Command execution timed out"
            suggested_fix = "Increase timeout or simplify the prompt"
        
        # Input/Prompt errors
        elif any(keyword in full_error for keyword in ["invalid input", "prompt", "malformed"]):
            error_type = "Input Error"
            description = "Invalid prompt or input format"
            suggested_fix = "Check prompt formatting and special characters"
        
        # Context length errors
        elif any(keyword in full_error for keyword in ["input is too long", "context length", "token limit", "too many tokens"]):
            error_type = "Context Length Error"
            description = "Input prompt exceeds model's context length limit"
            suggested_fix = "Shorten the prompt or use continue mode to reduce context"
        
        # Return code specific analysis
        if return_code == 1:
            if error_type == "Unknown Error":
                error_type = "General Error"
                description = "Command failed with exit code 1 - general error"
        elif return_code == 2:
            error_type = "Usage Error"
            description = "Command usage error - incorrect arguments or options"
            suggested_fix = "Check Claude CLI command syntax and arguments"
        elif return_code == 126:
            error_type = "Permission Error"
            description = "Command found but not executable"
            suggested_fix = "Check execute permissions on Claude CLI binary"
        elif return_code == 127:
            error_type = "Command Not Found"
            description = "Claude CLI command not found"
            suggested_fix = "Install Claude CLI or add to PATH"
        elif return_code == 130:
            error_type = "Interrupted"
            description = "Command was interrupted (Ctrl+C)"
            suggested_fix = "Command was manually interrupted"
        
        return {
            "type": error_type,
            "description": description,
            "suggested_fix": suggested_fix
        }
    
    async def _execute_claude_command(self, prompt: str, continue_mode: bool = False, retry_count: int = 0) -> Optional[str]:
        """Execute the claude CLI command with dangerous skip permissions for uninterrupted operation."""
        try:
            # Build command with --dangerously-skip-permissions for uninterrupted execution
            if continue_mode:
                cmd = ["claude", "--dangerously-skip-permissions", "-p", "-c", prompt]
            else:
                cmd = ["claude", "--dangerously-skip-permissions", "-p", prompt]
            
            # Estimate input tokens
            input_tokens = self._estimate_tokens(prompt)
            
            logger.info("🔧 Executing claude command (uninterrupted mode)", 
                       command=" ".join(cmd),
                       estimated_input_tokens=input_tokens,
                       retry_attempt=retry_count)
            
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
                
                # Estimate output tokens and calculate cost
                output_tokens = self._estimate_tokens(result)
                interaction_cost = self._calculate_token_cost(input_tokens, output_tokens)
                
                # Update cost tracking
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.total_cost += interaction_cost
                self.interaction_count += 1
                
                # Calculate average cost per interaction
                avg_cost_per_interaction = self.total_cost / self.interaction_count if self.interaction_count > 0 else 0
                
                logger.info("✅ Claude command executed successfully", 
                          response_length=len(result),
                          input_tokens=input_tokens,
                          output_tokens=output_tokens,
                          interaction_cost=f"${interaction_cost:.4f}",
                          total_cost=f"${self.total_cost:.4f}",
                          avg_cost_per_interaction=f"${avg_cost_per_interaction:.4f}",
                          total_interactions=self.interaction_count)
                
                return result
            else:
                # Comprehensive error logging
                stdout_msg = stdout.decode('utf-8').strip() if stdout else "No stdout"
                stderr_msg = stderr.decode('utf-8').strip() if stderr else "No stderr"
                
                # Analyze common error patterns
                error_analysis = self._analyze_claude_error(stderr_msg, stdout_msg, process.returncode)
                
                # Handle context length errors with automatic retry
                if error_analysis["type"] == "Context Length Error" and retry_count < 2:
                    logger.warning("🔄 Context length exceeded - attempting retry with shorter prompt", 
                                 retry_attempt=retry_count + 1)
                    
                    # Shorten the prompt and retry
                    shortened_prompt = self._shorten_prompt(prompt, continue_mode)
                    if shortened_prompt != prompt:
                        logger.info("✂️ Prompt shortened for retry", 
                                  original_length=len(prompt),
                                  shortened_length=len(shortened_prompt))
                        return await self._execute_claude_command(shortened_prompt, continue_mode, retry_count + 1)
                
                logger.error("❌ Claude command failed - DETAILED ERROR ANALYSIS", 
                           return_code=process.returncode,
                           stderr=stderr_msg,
                           stdout=stdout_msg,
                           error_type=error_analysis["type"],
                           error_description=error_analysis["description"],
                           suggested_fix=error_analysis["suggested_fix"],
                           command_executed=" ".join(cmd),
                           working_directory="/Users/rkondis/personalwork/trade-executor-cli",
                           retry_attempt=retry_count)
                
                return None
                
        except Exception as e:
            logger.error("❌ Error executing claude command", error=str(e))
            return None
    
    def _shorten_prompt(self, prompt: str, continue_mode: bool) -> str:
        """Shorten prompt to fit within context limits."""
        if continue_mode:
            # For monitoring, use ultra-short prompt
            return "Quick status: P&L, decision (hold/close), reason (1 sentence). Execute if closing."
        else:
            # For trade initiation, use condensed version
            trading_config = self.config['trading']
            coins = ', '.join(trading_config['coins'])
            
            return (
                f"Use Bybit MCP to execute profitable FUTURES trade on {coins}. "
                f"Target: 20% daily returns. Use linear perpetual contracts with leverage. "
                f"Analyze market, choose best coin, set leverage and position size. Execute with stop-loss and take-profit."
            )
    
    def _parse_trade_initiation(self, response: str) -> bool:
        """Parse claude response to determine if trade was initiated with enhanced detection."""
        if not response:
            return False
            
        response_lower = response.lower()
        
        # Enhanced indicators for successful trade initiation
        success_indicators = [
            "trade is now active",
            "position entry",
            "executed",
            "entry price", 
            "stop loss",
            "take profit",
            "position size",
            "order placed",
            "trade opened",
            "position opened",
            "buy order",
            "sell order",
            "long position",
            "short position",
            "leverage",
            "margin",
            "filled",
            "opened",
            "active",
            "initiated",
            "started",
            "placed"
        ]
        
        # Strong execution confirmations (single indicator is enough)
        strong_confirmations = [
            "order executed",
            "trade executed", 
            "position opened successfully",
            "order filled",
            "successfully opened",
            "execution confirmed",
            "trade initiated successfully",
            "position active"
        ]
        
        # Check for strong confirmations first
        for confirmation in strong_confirmations:
            if confirmation in response_lower:
                logger.info("📋 Trade initiation confirmed with strong indicator", 
                           indicator=confirmation, success=True)
                return True
        
        # Count regular indicators
        found_indicators = sum(1 for indicator in success_indicators 
                             if indicator in response_lower)
        
        # More lenient success criteria
        success = found_indicators >= 1  # Even 1 indicator can be enough
        
        # Special case: very short responses might still be successful
        if len(response.strip()) < 50 and any(word in response_lower for word in ["ok", "done", "yes", "executed", "filled", "opened"]):
            logger.info("📋 Trade initiation detected from brief response", 
                       response=response.strip(), success=True)
            return True
        
        logger.info("📋 Trade initiation analysis", 
                   indicators_found=found_indicators,
                   response_length=len(response),
                   success=success,
                   response_preview=response[:100] + "..." if len(response) > 100 else response)
        
        return success
    
    def _is_trade_completed(self, response: str) -> bool:
        """Check if the trade has been completed based on claude response with strict execution verification."""
        if not response:
            return False
            
        response_lower = response.lower()
        
        # Extract the actual decision first
        decision = "unknown"
        if "hold" in response_lower or "holding" in response_lower:
            decision = "hold"
        elif "close" in response_lower or "closing" in response_lower:
            decision = "close"
        elif "exit" in response_lower or "exiting" in response_lower:
            decision = "exit"
        
        # If decision is to hold, don't consider it completed
        if decision == "hold":
            logger.debug("🔄 Trade continues - decision is to hold", decision=decision)
            return False
        
        # For close/exit decisions, require STRICT execution confirmation
        if decision in ["close", "exit"]:
            # Look for actual execution confirmations, not just intentions
            execution_confirmations = [
                "order executed",
                "position closed successfully",
                "trade executed",
                "order filled",
                "successfully closed",
                "execution confirmed",
                "order completed",
                "position liquidated",
                "trade closed successfully",
                "exit executed"
            ]
            
            # Check for actual execution confirmation
            execution_confirmed = any(confirmation in response_lower for confirmation in execution_confirmations)
            
            if execution_confirmed:
                logger.info("🏁 Trade completion confirmed with execution", decision=decision, execution_confirmed=True)
                return True
            else:
                # Claude said close but no execution confirmation - continue monitoring
                logger.warning("⚠️ Close decision detected but no execution confirmation - continuing to monitor", 
                             decision=decision, execution_confirmed=False)
                return False
        
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
    
    def _extract_trade_initiation_details(self, response: str) -> Dict[str, str]:
        """Extract detailed trade information from Claude's trade initiation response."""
        if not response:
            return {
                "coin": "Unknown",
                "side": "Unknown", 
                "entry_price": "Unknown",
                "position_size": "Unknown",
                "leverage": "Unknown",
                "stop_loss": "Unknown",
                "take_profit": "Unknown"
            }
        
        response_lower = response.lower()
        
        # Extract coin/symbol
        coin = "Unknown"
        coins = ["btc", "bitcoin", "eth", "ethereum", "sol", "solana", "xrp", "ripple", "doge", "dogecoin", "pepe", "link", "chainlink"]
        for c in coins:
            if c in response_lower:
                if c in ["btc", "bitcoin"]:
                    coin = "BTC"
                elif c in ["eth", "ethereum"]:
                    coin = "ETH"
                elif c in ["sol", "solana"]:
                    coin = "SOL"
                elif c in ["xrp", "ripple"]:
                    coin = "XRP"
                elif c in ["doge", "dogecoin"]:
                    coin = "DOGE"
                elif c == "pepe":
                    coin = "PEPE"
                elif c in ["link", "chainlink"]:
                    coin = "LINK"
                break
        
        # Extract side (buy/sell, long/short)
        side = "Unknown"
        if "buy" in response_lower or "long" in response_lower:
            side = "Long"
        elif "sell" in response_lower or "short" in response_lower:
            side = "Short"
        
        # Extract entry price using regex
        entry_price = "Unknown"
        price_patterns = [
            r'\$([0-9,]+\.?[0-9]*)',  # $50,000 or $50000.50
            r'([0-9,]+\.?[0-9]*)\s*(?:usd|usdt)',  # 50000 USD/USDT
            r'entry.*?([0-9,]+\.?[0-9]*)',  # entry price 50000
            r'price.*?([0-9,]+\.?[0-9]*)',  # price 50000
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                entry_price = f"${matches[0].replace(',', '')}"
                break
        
        # Extract position size
        position_size = "Unknown"
        size_patterns = [
            r'([0-9]+\.?[0-9]*)\s*%',  # 10% or 10.5%
            r'([0-9]+\.?[0-9]*)\s*(?:btc|eth|sol|xrp|doge|pepe|link)',  # 0.1 BTC
            r'size.*?([0-9]+\.?[0-9]*)',  # size 0.1
            r'quantity.*?([0-9]+\.?[0-9]*)',  # quantity 0.1
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                if '%' in response_lower:
                    position_size = f"{matches[0]}%"
                else:
                    position_size = f"{matches[0]} {coin}"
                break
        
        # Extract leverage
        leverage = "Unknown"
        leverage_patterns = [
            r'([0-9]+)x\s*leverage',  # 10x leverage
            r'leverage.*?([0-9]+)',  # leverage 10
            r'([0-9]+)x',  # 10x
        ]
        
        for pattern in leverage_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                leverage = f"{matches[0]}x"
                break
        
        # Extract stop loss
        stop_loss = "Unknown"
        sl_patterns = [
            r'stop.*?loss.*?\$([0-9,]+\.?[0-9]*)',  # stop loss $45000
            r'sl.*?\$([0-9,]+\.?[0-9]*)',  # SL $45000
            r'stop.*?([0-9,]+\.?[0-9]*)',  # stop 45000
        ]
        
        for pattern in sl_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                stop_loss = f"${matches[0].replace(',', '')}"
                break
        
        # Extract take profit
        take_profit = "Unknown"
        tp_patterns = [
            r'take.*?profit.*?\$([0-9,]+\.?[0-9]*)',  # take profit $55000
            r'tp.*?\$([0-9,]+\.?[0-9]*)',  # TP $55000
            r'target.*?\$([0-9,]+\.?[0-9]*)',  # target $55000
        ]
        
        for pattern in tp_patterns:
            matches = re.findall(pattern, response_lower)
            if matches:
                take_profit = f"${matches[0].replace(',', '')}"
                break
        
        return {
            "coin": coin,
            "side": side,
            "entry_price": entry_price,
            "position_size": position_size,
            "leverage": leverage,
            "stop_loss": stop_loss,
            "take_profit": take_profit
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
