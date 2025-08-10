"""Core trading engine that orchestrates the automated trading process."""

import asyncio
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import structlog

from .config import ConfigManager
from .session_manager import SessionManager
from ..integrations.bedrock_client import BedrockClient
from ..integrations.bybit_client import BybitClient
from ..risk.risk_manager import RiskManager

logger = structlog.get_logger(__name__)


class TradeStatus(Enum):
    """Trade status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ERROR = "error"


class TradingEngine:
    """Main trading engine that manages the automated trading process."""
    
    def __init__(self, config_manager: ConfigManager, mcp_client):
        self.config_manager = config_manager
        self.mcp_client = mcp_client
        
        # Initialize components
        self.bedrock_client = BedrockClient(config_manager.get_bedrock_config())
        self.bybit_client = BybitClient(config_manager.get_bybit_config(), mcp_client)
        self.session_manager = SessionManager(config_manager.get_database_config())
        self.risk_manager = RiskManager(config_manager.get_trading_config())
        
        # Trading state
        self.current_session = None
        self.current_trade = None
        self.is_running = False
        self.monitoring_task = None
        self.news_task = None
        
        # Cached data
        self.latest_market_data = {}
        self.latest_news_data = {}
        
        logger.info("Trading engine initialized")
    
    async def start_trading_session(self) -> Dict[str, Any]:
        """Start a new trading session."""
        try:
            # Check if already running
            if self.is_running:
                return {"error": "Trading session already active"}
            
            # Validate configuration
            config_errors = self.config_manager.validate_config()
            if config_errors:
                return {"error": f"Configuration errors: {', '.join(config_errors)}"}
            
            # Check daily trade limits
            if not await self.risk_manager.can_start_new_trade():
                return {"error": "Daily trade limit reached or cooldown period active"}
            
            # Create new session
            self.current_session = await self.session_manager.create_session()
            
            # Start monitoring tasks
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.news_task = asyncio.create_task(self._news_loop())
            
            logger.info("Trading session started", session_id=self.current_session["id"])
            
            # Perform initial market analysis
            await self._perform_initial_analysis()
            
            return {
                "status": "success",
                "session_id": self.current_session["id"],
                "message": "Trading session started successfully"
            }
            
        except Exception as e:
            logger.error("Failed to start trading session", error=str(e))
            return {"error": f"Failed to start session: {str(e)}"}
    
    async def stop_trading_session(self, emergency: bool = False) -> Dict[str, Any]:
        """Stop the current trading session."""
        try:
            if not self.is_running:
                return {"error": "No active trading session"}
            
            # Stop monitoring tasks
            self.is_running = False
            
            if self.monitoring_task:
                self.monitoring_task.cancel()
            
            if self.news_task:
                self.news_task.cancel()
            
            # Handle active trade
            if self.current_trade and self.current_trade["status"] == TradeStatus.ACTIVE.value:
                if emergency:
                    await self._emergency_close_position()
                else:
                    await self._close_position_gracefully()
            
            # End session
            if self.current_session:
                await self.session_manager.end_session(
                    self.current_session["id"],
                    emergency=emergency
                )
            
            # Reset state
            self.current_session = None
            self.current_trade = None
            
            logger.info("Trading session stopped", emergency=emergency)
            
            return {
                "status": "success",
                "message": "Trading session stopped successfully"
            }
            
        except Exception as e:
            logger.error("Failed to stop trading session", error=str(e))
            return {"error": f"Failed to stop session: {str(e)}"}
    
    async def get_session_status(self) -> Dict[str, Any]:
        """Get current session status."""
        try:
            if not self.is_running or not self.current_session:
                return {
                    "active": False,
                    "message": "No active trading session"
                }
            
            # Get current positions
            positions = await self.bybit_client.get_current_positions()
            
            # Get account balance
            balance = await self.bybit_client.get_account_balance()
            
            status = {
                "active": True,
                "session_id": self.current_session["id"],
                "session_start": self.current_session["created_at"],
                "current_trade": self.current_trade,
                "positions": positions,
                "balance": balance,
                "latest_market_data": self.latest_market_data,
                "latest_news_summary": self._get_news_summary()
            }
            
            return status
            
        except Exception as e:
            logger.error("Failed to get session status", error=str(e))
            return {"error": f"Failed to get status: {str(e)}"}
    
    async def _perform_initial_analysis(self):
        """Perform initial market analysis to identify trading opportunities."""
        try:
            logger.info("Performing initial market analysis")
            
            # Get account balance
            balance_data = await self.bybit_client.get_account_balance()
            available_balance = self._extract_available_balance(balance_data)
            
            if available_balance < 10:  # Minimum $10 to trade
                logger.warning("Insufficient balance for trading", balance=available_balance)
                return
            
            # Analyze each allowed trading pair
            trading_config = self.config_manager.get_trading_config()
            best_opportunity = None
            best_score = 0
            
            for symbol in trading_config.allowed_pairs:
                try:
                    # Get market data
                    market_data = await self.bybit_client.get_market_data(symbol)
                    self.latest_market_data[symbol] = market_data
                    
                    # Analyze market conditions
                    analysis = await self.bedrock_client.analyze_market_conditions(market_data)
                    
                    # Score the opportunity
                    opportunity_score = self._score_trading_opportunity(analysis)
                    
                    if opportunity_score > best_score:
                        best_score = opportunity_score
                        best_opportunity = {
                            "symbol": symbol,
                            "market_data": market_data,
                            "analysis": analysis,
                            "score": opportunity_score
                        }
                    
                    # Small delay between API calls
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.warning("Failed to analyze symbol", symbol=symbol, error=str(e))
                    continue
            
            # Make trading decision if good opportunity found
            if best_opportunity and best_score > 0.6:  # Minimum confidence threshold
                await self._execute_trading_decision(best_opportunity, available_balance)
            else:
                logger.info("No suitable trading opportunities found", best_score=best_score)
            
        except Exception as e:
            logger.error("Failed to perform initial analysis", error=str(e))
    
    async def _execute_trading_decision(self, opportunity: Dict[str, Any], available_balance: float):
        """Execute a trading decision based on analysis."""
        try:
            symbol = opportunity["symbol"]
            market_data = opportunity["market_data"]
            analysis = opportunity["analysis"]
            
            # Get portfolio data
            portfolio_data = {
                "available_balance": available_balance,
                "current_positions": await self.bybit_client.get_current_positions(),
                "risk_limits": self.risk_manager.get_risk_limits()
            }
            
            # Make trading decision
            decision = await self.bedrock_client.make_trading_decision(
                market_data=market_data,
                news_data=self.latest_news_data,
                portfolio_data=portfolio_data
            )
            
            logger.info("Trading decision made", symbol=symbol, decision=decision["action"])
            
            if decision["action"] in ["buy", "sell"]:
                await self._place_trade(decision, available_balance)
            
        except Exception as e:
            logger.error("Failed to execute trading decision", error=str(e))
    
    async def _place_trade(self, decision: Dict[str, Any], available_balance: float):
        """Place a trade based on LLM decision."""
        try:
            symbol = decision["symbol"]
            side = "Buy" if decision["action"] == "buy" else "Sell"
            
            # Calculate position size
            position_size_info = self.bybit_client.calculate_position_size(
                available_balance=available_balance,
                percentage=decision["position_size_percent"],
                price=float(decision["entry_price_target"])
            )
            
            # Validate order parameters
            validation = await self.bybit_client.validate_order_parameters(
                symbol=symbol,
                side=side,
                quantity=str(position_size_info["quantity"]),
                price=decision.get("entry_price_target")
            )
            
            if not validation["valid"]:
                logger.error("Order validation failed", errors=validation["errors"])
                return
            
            # Generate unique order link ID
            order_link_id = f"trade_{uuid.uuid4().hex[:8]}"
            
            # Place the order
            order_response = await self.bybit_client.place_order(
                symbol=symbol,
                side=side,
                order_type="Market",  # Start with market orders for simplicity
                quantity=str(position_size_info["quantity"]),
                stop_loss=decision.get("stop_loss"),
                take_profit=decision.get("take_profit"),
                order_link_id=order_link_id
            )
            
            # Create trade record
            self.current_trade = {
                "id": str(uuid.uuid4()),
                "session_id": self.current_session["id"],
                "symbol": symbol,
                "side": side,
                "quantity": position_size_info["quantity"],
                "entry_price": decision["entry_price_target"],
                "stop_loss": decision.get("stop_loss"),
                "take_profit": decision.get("take_profit"),
                "order_id": order_response.get("result", {}).get("orderId"),
                "order_link_id": order_link_id,
                "status": TradeStatus.ACTIVE.value,
                "created_at": datetime.now().isoformat(),
                "decision_reasoning": decision["reasoning"],
                "confidence": decision["confidence"]
            }
            
            # Save trade to database
            await self.session_manager.save_trade(self.current_trade)
            
            logger.info(
                "Trade placed successfully",
                symbol=symbol,
                side=side,
                quantity=position_size_info["quantity"],
                order_id=self.current_trade["order_id"]
            )
            
        except Exception as e:
            logger.error("Failed to place trade", error=str(e))
    
    async def _monitoring_loop(self):
        """Main monitoring loop that runs every 15 minutes."""
        try:
            trading_config = self.config_manager.get_trading_config()
            interval = trading_config.price_check_interval_minutes * 60  # Convert to seconds
            
            while self.is_running:
                try:
                    await self._monitor_current_trade()
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in monitoring loop", error=str(e))
                    await asyncio.sleep(60)  # Wait 1 minute before retrying
                    
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
    
    async def _news_loop(self):
        """News monitoring loop that runs every hour."""
        try:
            trading_config = self.config_manager.get_trading_config()
            interval = trading_config.news_check_interval_minutes * 60  # Convert to seconds
            
            while self.is_running:
                try:
                    await self._fetch_and_analyze_news()
                    await asyncio.sleep(interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Error in news loop", error=str(e))
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying
                    
        except asyncio.CancelledError:
            logger.info("News loop cancelled")
    
    async def _monitor_current_trade(self):
        """Monitor the current active trade."""
        try:
            if not self.current_trade or self.current_trade["status"] != TradeStatus.ACTIVE.value:
                return
            
            symbol = self.current_trade["symbol"]
            
            # Get current market data
            market_data = await self.bybit_client.get_market_data(symbol)
            self.latest_market_data[symbol] = market_data
            
            # Get current position
            positions = await self.bybit_client.get_current_positions(symbol)
            
            # Evaluate position
            evaluation = await self.bedrock_client.evaluate_position(
                position_data=self.current_trade,
                market_data=market_data,
                news_data=self.latest_news_data
            )
            
            logger.info(
                "Position evaluated",
                symbol=symbol,
                action=evaluation["action"],
                urgency=evaluation["urgency"]
            )
            
            # Act on evaluation
            if evaluation["action"] == "close":
                await self._close_position_gracefully()
            elif evaluation["action"] == "adjust_stop":
                await self._adjust_stop_loss(evaluation.get("new_stop_loss"))
            elif evaluation["action"] == "adjust_target":
                await self._adjust_take_profit(evaluation.get("new_take_profit"))
            
        except Exception as e:
            logger.error("Failed to monitor current trade", error=str(e))
    
    async def _fetch_and_analyze_news(self):
        """Fetch and analyze news from various sources."""
        try:
            # This would integrate with news MCP servers
            # For now, we'll create a placeholder
            self.latest_news_data = {
                "timestamp": datetime.now().isoformat(),
                "sources": [],
                "sentiment": "neutral",
                "impact": "low"
            }
            
            logger.info("News data updated")
            
        except Exception as e:
            logger.error("Failed to fetch news", error=str(e))
    
    async def _close_position_gracefully(self):
        """Close the current position gracefully."""
        try:
            if not self.current_trade:
                return
            
            symbol = self.current_trade["symbol"]
            
            # Cancel any open orders first
            open_orders = await self.bybit_client.get_open_orders(symbol)
            for order in open_orders.get("result", {}).get("list", []):
                await self.bybit_client.cancel_order(symbol, order_id=order["orderId"])
            
            # Close position with market order
            opposite_side = "Sell" if self.current_trade["side"] == "Buy" else "Buy"
            
            await self.bybit_client.place_order(
                symbol=symbol,
                side=opposite_side,
                order_type="Market",
                quantity=str(self.current_trade["quantity"])
            )
            
            # Update trade status
            self.current_trade["status"] = TradeStatus.CLOSED.value
            self.current_trade["closed_at"] = datetime.now().isoformat()
            
            await self.session_manager.update_trade(self.current_trade)
            
            logger.info("Position closed gracefully", symbol=symbol)
            
            # Start cooldown before next trade
            await self._start_cooldown()
            
        except Exception as e:
            logger.error("Failed to close position gracefully", error=str(e))
    
    async def _emergency_close_position(self):
        """Emergency close of current position."""
        try:
            if not self.current_trade:
                return
            
            symbol = self.current_trade["symbol"]
            
            # Market close immediately
            opposite_side = "Sell" if self.current_trade["side"] == "Buy" else "Buy"
            
            await self.bybit_client.place_order(
                symbol=symbol,
                side=opposite_side,
                order_type="Market",
                quantity=str(self.current_trade["quantity"])
            )
            
            self.current_trade["status"] = TradeStatus.CLOSED.value
            self.current_trade["closed_at"] = datetime.now().isoformat()
            self.current_trade["emergency_close"] = True
            
            await self.session_manager.update_trade(self.current_trade)
            
            logger.warning("Emergency position close executed", symbol=symbol)
            
        except Exception as e:
            logger.error("Failed to emergency close position", error=str(e))
    
    async def _adjust_stop_loss(self, new_stop_loss: Optional[str]):
        """Adjust stop loss for current position."""
        if not new_stop_loss or not self.current_trade:
            return
        
        try:
            await self.bybit_client.set_trading_stop(
                symbol=self.current_trade["symbol"],
                stop_loss=new_stop_loss
            )
            
            self.current_trade["stop_loss"] = new_stop_loss
            await self.session_manager.update_trade(self.current_trade)
            
            logger.info("Stop loss adjusted", new_stop_loss=new_stop_loss)
            
        except Exception as e:
            logger.error("Failed to adjust stop loss", error=str(e))
    
    async def _adjust_take_profit(self, new_take_profit: Optional[str]):
        """Adjust take profit for current position."""
        if not new_take_profit or not self.current_trade:
            return
        
        try:
            await self.bybit_client.set_trading_stop(
                symbol=self.current_trade["symbol"],
                take_profit=new_take_profit
            )
            
            self.current_trade["take_profit"] = new_take_profit
            await self.session_manager.update_trade(self.current_trade)
            
            logger.info("Take profit adjusted", new_take_profit=new_take_profit)
            
        except Exception as e:
            logger.error("Failed to adjust take profit", error=str(e))
    
    async def _start_cooldown(self):
        """Start cooldown period before next trade."""
        trading_config = self.config_manager.get_trading_config()
        cooldown_minutes = trading_config.cooldown_between_trades_minutes
        
        logger.info("Starting cooldown period", duration_minutes=cooldown_minutes)
        
        # Wait for cooldown period
        await asyncio.sleep(cooldown_minutes * 60)
        
        # Reset for next trade
        self.current_trade = None
        
        # Perform new analysis for next trade
        await self._perform_initial_analysis()
    
    def _extract_available_balance(self, balance_data: Dict[str, Any]) -> float:
        """Extract available balance from balance response."""
        try:
            # This depends on the structure of Bybit's balance response
            # Adjust based on actual response format
            result = balance_data.get("result", {})
            if "list" in result and result["list"]:
                account = result["list"][0]
                if "coin" in account and account["coin"]:
                    for coin in account["coin"]:
                        if coin.get("coin") == "USDT":
                            return float(coin.get("availableToWithdraw", 0))
            return 0.0
        except Exception as e:
            logger.error("Failed to extract available balance", error=str(e))
            return 0.0
    
    def _score_trading_opportunity(self, analysis: Dict[str, Any]) -> float:
        """Score a trading opportunity based on analysis."""
        try:
            base_score = analysis.get("confidence", 0.5)
            
            # Adjust score based on various factors
            if analysis.get("risk_level") == "low":
                base_score += 0.1
            elif analysis.get("risk_level") == "high":
                base_score -= 0.2
            
            if analysis.get("volatility") == "high":
                base_score -= 0.1
            
            if analysis.get("trend") in ["bullish", "bearish"]:
                base_score += 0.1
            
            return max(0.0, min(1.0, base_score))
            
        except Exception as e:
            logger.error("Failed to score opportunity", error=str(e))
            return 0.0
    
    def _get_news_summary(self) -> Dict[str, Any]:
        """Get a summary of latest news data."""
        if not self.latest_news_data:
            return {"status": "no_data"}
        
        return {
            "timestamp": self.latest_news_data.get("timestamp"),
            "sentiment": self.latest_news_data.get("sentiment"),
            "impact": self.latest_news_data.get("impact"),
            "source_count": len(self.latest_news_data.get("sources", []))
        }
