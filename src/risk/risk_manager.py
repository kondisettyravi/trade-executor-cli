"""Risk management system for automated trading."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog

from ..core.config import TradingConfig

logger = structlog.get_logger(__name__)


class RiskManager:
    """Risk management system to control trading exposure and losses."""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_trade_time = None
        self.emergency_stop_triggered = False
        
        logger.info("Risk manager initialized")
    
    async def can_start_new_trade(self) -> bool:
        """Check if a new trade can be started based on risk rules."""
        try:
            # Check daily trade limit
            if self.daily_trades >= self.config.max_trades_per_day:
                logger.warning(
                    "Daily trade limit reached",
                    daily_trades=self.daily_trades,
                    limit=self.config.max_trades_per_day
                )
                return False
            
            # Check cooldown period
            if self.last_trade_time:
                time_since_last = datetime.now() - self.last_trade_time
                cooldown_period = timedelta(minutes=self.config.cooldown_between_trades_minutes)
                
                if time_since_last < cooldown_period:
                    remaining_cooldown = cooldown_period - time_since_last
                    logger.info(
                        "Cooldown period active",
                        remaining_minutes=remaining_cooldown.total_seconds() / 60
                    )
                    return False
            
            # Check daily loss limit
            if self.daily_pnl <= -self.config.max_daily_loss_percent:
                logger.warning(
                    "Daily loss limit reached",
                    daily_pnl=self.daily_pnl,
                    limit=self.config.max_daily_loss_percent
                )
                return False
            
            # Check emergency stop
            if self.emergency_stop_triggered:
                logger.warning("Emergency stop is active")
                return False
            
            return True
            
        except Exception as e:
            logger.error("Failed to check trade eligibility", error=str(e))
            return False
    
    async def validate_position_size(
        self,
        available_balance: float,
        position_size_percent: int,
        symbol: str
    ) -> Dict[str, Any]:
        """Validate if the proposed position size is within risk limits."""
        try:
            # Check if position size is in allowed range
            if position_size_percent not in self.config.position_sizes:
                return {
                    "valid": False,
                    "reason": f"Position size {position_size_percent}% not in allowed sizes: {self.config.position_sizes}"
                }
            
            # Calculate position value
            position_value = available_balance * (position_size_percent / 100)
            
            # Check minimum position size
            if position_value < 10:  # Minimum $10 position
                return {
                    "valid": False,
                    "reason": f"Position value ${position_value:.2f} below minimum $10"
                }
            
            # Check maximum position size (safety check)
            if position_size_percent > 25:
                return {
                    "valid": False,
                    "reason": f"Position size {position_size_percent}% exceeds maximum 25%"
                }
            
            return {
                "valid": True,
                "position_value": position_value,
                "risk_level": self._assess_position_risk(position_size_percent)
            }
            
        except Exception as e:
            logger.error("Failed to validate position size", error=str(e))
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}"
            }
    
    async def check_stop_loss_requirements(
        self,
        entry_price: float,
        stop_loss: Optional[float],
        side: str
    ) -> Dict[str, Any]:
        """Check if stop loss is properly set and within risk limits."""
        try:
            if not stop_loss:
                return {
                    "valid": False,
                    "reason": "Stop loss is required for all trades"
                }
            
            # Calculate stop loss percentage
            if side.lower() == "buy":
                stop_loss_percent = ((entry_price - stop_loss) / entry_price) * 100
            else:  # sell
                stop_loss_percent = ((stop_loss - entry_price) / entry_price) * 100
            
            # Check if stop loss is within acceptable range
            if stop_loss_percent > self.config.max_position_loss_percent:
                return {
                    "valid": False,
                    "reason": f"Stop loss {stop_loss_percent:.2f}% exceeds maximum {self.config.max_position_loss_percent}%"
                }
            
            # Check if stop loss is too tight (less than 0.5%)
            if stop_loss_percent < 0.5:
                return {
                    "valid": False,
                    "reason": f"Stop loss {stop_loss_percent:.2f}% too tight, minimum 0.5%"
                }
            
            return {
                "valid": True,
                "stop_loss_percent": stop_loss_percent,
                "risk_level": "low" if stop_loss_percent <= 2 else "medium" if stop_loss_percent <= 4 else "high"
            }
            
        except Exception as e:
            logger.error("Failed to check stop loss requirements", error=str(e))
            return {
                "valid": False,
                "reason": f"Stop loss validation error: {str(e)}"
            }
    
    async def monitor_position_risk(
        self,
        current_price: float,
        entry_price: float,
        side: str,
        position_value: float
    ) -> Dict[str, Any]:
        """Monitor current position risk and suggest actions."""
        try:
            # Calculate current P&L percentage
            if side.lower() == "buy":
                pnl_percent = ((current_price - entry_price) / entry_price) * 100
            else:  # sell
                pnl_percent = ((entry_price - current_price) / entry_price) * 100
            
            # Calculate unrealized P&L in dollars
            unrealized_pnl = position_value * (pnl_percent / 100)
            
            risk_assessment = {
                "current_price": current_price,
                "entry_price": entry_price,
                "pnl_percent": pnl_percent,
                "unrealized_pnl": unrealized_pnl,
                "risk_level": "low",
                "action": "hold",
                "urgency": "low"
            }
            
            # Assess risk level and suggest actions
            if pnl_percent <= -self.config.emergency_stop_loss_percent:
                risk_assessment.update({
                    "risk_level": "critical",
                    "action": "emergency_close",
                    "urgency": "immediate",
                    "reason": f"Emergency stop loss triggered at {pnl_percent:.2f}%"
                })
            elif pnl_percent <= -self.config.max_position_loss_percent:
                risk_assessment.update({
                    "risk_level": "high",
                    "action": "close",
                    "urgency": "high",
                    "reason": f"Maximum position loss reached at {pnl_percent:.2f}%"
                })
            elif pnl_percent <= -3:  # Warning level
                risk_assessment.update({
                    "risk_level": "medium",
                    "action": "monitor_closely",
                    "urgency": "medium",
                    "reason": f"Position showing loss of {pnl_percent:.2f}%"
                })
            elif pnl_percent >= 10:  # Consider taking profits
                risk_assessment.update({
                    "risk_level": "low",
                    "action": "consider_profit_taking",
                    "urgency": "low",
                    "reason": f"Position showing good profit of {pnl_percent:.2f}%"
                })
            
            return risk_assessment
            
        except Exception as e:
            logger.error("Failed to monitor position risk", error=str(e))
            return {
                "risk_level": "unknown",
                "action": "hold",
                "urgency": "low",
                "error": str(e)
            }
    
    async def update_daily_metrics(self, trade_pnl: float):
        """Update daily trading metrics."""
        try:
            self.daily_trades += 1
            self.daily_pnl += trade_pnl
            self.last_trade_time = datetime.now()
            
            logger.info(
                "Daily metrics updated",
                daily_trades=self.daily_trades,
                daily_pnl=self.daily_pnl
            )
            
            # Check if daily loss limit is breached
            if self.daily_pnl <= -self.config.max_daily_loss_percent:
                await self.trigger_daily_stop()
            
        except Exception as e:
            logger.error("Failed to update daily metrics", error=str(e))
    
    async def trigger_emergency_stop(self, reason: str):
        """Trigger emergency stop for all trading activities."""
        try:
            self.emergency_stop_triggered = True
            
            logger.critical(
                "Emergency stop triggered",
                reason=reason,
                timestamp=datetime.now().isoformat()
            )
            
            # This would typically notify external systems or administrators
            # For now, we'll just log the event
            
        except Exception as e:
            logger.error("Failed to trigger emergency stop", error=str(e))
    
    async def trigger_daily_stop(self):
        """Trigger daily trading stop due to loss limits."""
        try:
            logger.warning(
                "Daily trading stop triggered",
                daily_pnl=self.daily_pnl,
                daily_trades=self.daily_trades,
                limit=self.config.max_daily_loss_percent
            )
            
            # Set flag to prevent new trades
            self.emergency_stop_triggered = True
            
        except Exception as e:
            logger.error("Failed to trigger daily stop", error=str(e))
    
    async def reset_daily_limits(self):
        """Reset daily limits (typically called at start of new trading day)."""
        try:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.emergency_stop_triggered = False
            self.last_trade_time = None
            
            logger.info("Daily limits reset for new trading day")
            
        except Exception as e:
            logger.error("Failed to reset daily limits", error=str(e))
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """Get current risk limits and status."""
        return {
            "max_daily_loss_percent": self.config.max_daily_loss_percent,
            "max_position_loss_percent": self.config.max_position_loss_percent,
            "emergency_stop_loss_percent": self.config.emergency_stop_loss_percent,
            "max_trades_per_day": self.config.max_trades_per_day,
            "cooldown_between_trades_minutes": self.config.cooldown_between_trades_minutes,
            "allowed_position_sizes": self.config.position_sizes,
            "current_daily_trades": self.daily_trades,
            "current_daily_pnl": self.daily_pnl,
            "emergency_stop_active": self.emergency_stop_triggered,
            "last_trade_time": self.last_trade_time.isoformat() if self.last_trade_time else None
        }
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status summary."""
        try:
            # Calculate remaining trade capacity
            remaining_trades = max(0, self.config.max_trades_per_day - self.daily_trades)
            
            # Calculate remaining loss capacity
            remaining_loss_capacity = max(0, self.config.max_daily_loss_percent + self.daily_pnl)
            
            # Determine overall risk level
            if self.emergency_stop_triggered:
                overall_risk = "critical"
            elif remaining_trades == 0 or remaining_loss_capacity <= 1:
                overall_risk = "high"
            elif remaining_trades <= 1 or remaining_loss_capacity <= 3:
                overall_risk = "medium"
            else:
                overall_risk = "low"
            
            return {
                "overall_risk_level": overall_risk,
                "can_trade": not self.emergency_stop_triggered and remaining_trades > 0,
                "remaining_trades": remaining_trades,
                "remaining_loss_capacity_percent": remaining_loss_capacity,
                "daily_pnl": self.daily_pnl,
                "daily_trades": self.daily_trades,
                "emergency_stop_active": self.emergency_stop_triggered,
                "cooldown_active": self._is_cooldown_active()
            }
            
        except Exception as e:
            logger.error("Failed to get risk status", error=str(e))
            return {
                "overall_risk_level": "unknown",
                "can_trade": False,
                "error": str(e)
            }
    
    def _assess_position_risk(self, position_size_percent: int) -> str:
        """Assess risk level based on position size."""
        if position_size_percent <= 10:
            return "low"
        elif position_size_percent <= 20:
            return "medium"
        else:
            return "high"
    
    def _is_cooldown_active(self) -> bool:
        """Check if cooldown period is currently active."""
        if not self.last_trade_time:
            return False
        
        time_since_last = datetime.now() - self.last_trade_time
        cooldown_period = timedelta(minutes=self.config.cooldown_between_trades_minutes)
        
        return time_since_last < cooldown_period
    
    async def validate_trade_parameters(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        position_size_percent: int,
        available_balance: float
    ) -> Dict[str, Any]:
        """Comprehensive validation of all trade parameters."""
        try:
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "risk_assessment": {}
            }
            
            # Check if new trade is allowed
            if not await self.can_start_new_trade():
                validation_results["valid"] = False
                validation_results["errors"].append("New trade not allowed due to risk limits")
            
            # Validate position size
            position_validation = await self.validate_position_size(
                available_balance, position_size_percent, symbol
            )
            if not position_validation["valid"]:
                validation_results["valid"] = False
                validation_results["errors"].append(position_validation["reason"])
            
            # Validate stop loss
            if stop_loss:
                stop_loss_validation = await self.check_stop_loss_requirements(
                    entry_price, stop_loss, side
                )
                if not stop_loss_validation["valid"]:
                    validation_results["valid"] = False
                    validation_results["errors"].append(stop_loss_validation["reason"])
                else:
                    validation_results["risk_assessment"]["stop_loss"] = stop_loss_validation
            
            # Basic parameter validation
            if quantity <= 0:
                validation_results["valid"] = False
                validation_results["errors"].append("Quantity must be positive")
            
            if entry_price <= 0:
                validation_results["valid"] = False
                validation_results["errors"].append("Entry price must be positive")
            
            # Risk assessment
            validation_results["risk_assessment"]["position_size"] = position_validation
            validation_results["risk_assessment"]["overall_risk"] = self.get_risk_status()
            
            return validation_results
            
        except Exception as e:
            logger.error("Failed to validate trade parameters", error=str(e))
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "risk_assessment": {}
            }
