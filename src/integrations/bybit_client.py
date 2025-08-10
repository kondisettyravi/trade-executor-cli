"""Bybit client wrapper for MCP integration."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog

from ..core.config import BybitConfig

logger = structlog.get_logger(__name__)


class BybitClient:
    """Client for interacting with Bybit exchange via MCP server."""
    
    def __init__(self, config: BybitConfig, mcp_client):
        self.config = config
        self.mcp_client = mcp_client
        self.category = config.category
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance information."""
        try:
            # Use the MCP tool to get wallet balance
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_wallet_balance",
                arguments={
                    "accountType": "UNIFIED" if self.category == "spot" else "CONTRACT"
                }
            )
            
            logger.info("Retrieved account balance", response_keys=list(response.keys()))
            return response
            
        except Exception as e:
            logger.error("Failed to get account balance", error=str(e))
            raise
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive market data for a symbol."""
        try:
            # Get ticker data
            ticker_data = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_tickers",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            
            # Get orderbook data
            orderbook_data = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_orderbook",
                arguments={
                    "category": self.category,
                    "symbol": symbol,
                    "limit": 25
                }
            )
            
            # Get recent kline data (1 hour intervals, last 24 hours)
            kline_data = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_kline",
                arguments={
                    "category": self.category,
                    "symbol": symbol,
                    "interval": "60",  # 1 hour
                    "limit": 24
                }
            )
            
            # Combine all market data
            market_data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "ticker": ticker_data,
                "orderbook": orderbook_data,
                "klines": kline_data,
                "category": self.category
            }
            
            logger.info("Retrieved market data", symbol=symbol)
            return market_data
            
        except Exception as e:
            logger.error("Failed to get market data", symbol=symbol, error=str(e))
            raise
    
    async def get_current_positions(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get current positions."""
        try:
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_positions",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            
            logger.info("Retrieved positions", symbol=symbol)
            return response
            
        except Exception as e:
            logger.error("Failed to get positions", symbol=symbol, error=str(e))
            raise
    
    async def place_order(
        self,
        symbol: str,
        side: str,  # "Buy" or "Sell"
        order_type: str,  # "Market" or "Limit"
        quantity: str,
        price: Optional[str] = None,
        stop_loss: Optional[str] = None,
        take_profit: Optional[str] = None,
        order_link_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place a trading order."""
        try:
            # Prepare order arguments
            order_args = {
                "category": self.category,
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": quantity
            }
            
            # Add optional parameters
            if price:
                order_args["price"] = price
            
            if stop_loss:
                order_args["stopLoss"] = stop_loss
                order_args["slOrderType"] = "Market"
            
            if take_profit:
                order_args["takeProfit"] = take_profit
                order_args["tpOrderType"] = "Market"
            
            if order_link_id:
                order_args["orderLinkId"] = order_link_id
            
            # Set time in force for limit orders
            if order_type == "Limit":
                order_args["timeInForce"] = "GTC"  # Good Till Cancel
            
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="place_order",
                arguments=order_args
            )
            
            logger.info(
                "Order placed successfully",
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                order_id=response.get("result", {}).get("orderId")
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Failed to place order",
                symbol=symbol,
                side=side,
                order_type=order_type,
                error=str(e)
            )
            raise
    
    async def cancel_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel an existing order."""
        try:
            cancel_args = {
                "category": self.category,
                "symbol": symbol
            }
            
            if order_id:
                cancel_args["orderId"] = order_id
            elif order_link_id:
                cancel_args["orderLinkId"] = order_link_id
            else:
                raise ValueError("Either order_id or order_link_id must be provided")
            
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="cancel_order",
                arguments=cancel_args
            )
            
            logger.info("Order cancelled successfully", symbol=symbol, order_id=order_id)
            return response
            
        except Exception as e:
            logger.error("Failed to cancel order", symbol=symbol, error=str(e))
            raise
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get open orders."""
        try:
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_open_orders",
                arguments={
                    "category": self.category,
                    "symbol": symbol,
                    "limit": 50
                }
            )
            
            logger.info("Retrieved open orders", symbol=symbol)
            return response
            
        except Exception as e:
            logger.error("Failed to get open orders", symbol=symbol, error=str(e))
            raise
    
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get order history."""
        try:
            history_args = {
                "category": self.category,
                "limit": limit
            }
            
            if symbol:
                history_args["symbol"] = symbol
            
            if start_time:
                history_args["startTime"] = int(start_time.timestamp() * 1000)
            
            if end_time:
                history_args["endTime"] = int(end_time.timestamp() * 1000)
            
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_order_history",
                arguments=history_args
            )
            
            logger.info("Retrieved order history", symbol=symbol)
            return response
            
        except Exception as e:
            logger.error("Failed to get order history", symbol=symbol, error=str(e))
            raise
    
    async def set_trading_stop(
        self,
        symbol: str,
        take_profit: Optional[str] = None,
        stop_loss: Optional[str] = None,
        trailing_stop: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set trading stop for existing position."""
        try:
            stop_args = {
                "category": self.category,
                "symbol": symbol
            }
            
            if take_profit:
                stop_args["takeProfit"] = take_profit
            
            if stop_loss:
                stop_args["stopLoss"] = stop_loss
            
            if trailing_stop:
                stop_args["trailingStop"] = trailing_stop
            
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="set_trading_stop",
                arguments=stop_args
            )
            
            logger.info("Trading stop set successfully", symbol=symbol)
            return response
            
        except Exception as e:
            logger.error("Failed to set trading stop", symbol=symbol, error=str(e))
            raise
    
    async def get_instruments_info(self, symbol: str) -> Dict[str, Any]:
        """Get instrument information."""
        try:
            response = await self.mcp_client.use_tool(
                server_name="bybit",
                tool_name="get_instruments_info",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            
            logger.info("Retrieved instrument info", symbol=symbol)
            return response
            
        except Exception as e:
            logger.error("Failed to get instrument info", symbol=symbol, error=str(e))
            raise
    
    def calculate_position_size(
        self, 
        available_balance: float, 
        percentage: int, 
        price: float
    ) -> Dict[str, Any]:
        """Calculate position size based on available balance and percentage."""
        try:
            # Calculate position value in USDT
            position_value = available_balance * (percentage / 100)
            
            # Calculate quantity based on price
            if self.category == "spot":
                # For spot trading, quantity is in base currency
                quantity = position_value / price
                # Round to appropriate decimal places (6 for most crypto)
                quantity = round(quantity, 6)
            else:
                # For futures, quantity might be different
                quantity = position_value / price
                quantity = round(quantity, 3)
            
            result = {
                "position_value_usdt": position_value,
                "quantity": quantity,
                "percentage": percentage,
                "price": price,
                "available_balance": available_balance
            }
            
            logger.info(
                "Calculated position size",
                percentage=percentage,
                position_value=position_value,
                quantity=quantity
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to calculate position size", error=str(e))
            raise
    
    async def validate_order_parameters(
        self,
        symbol: str,
        side: str,
        quantity: str,
        price: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate order parameters against instrument specifications."""
        try:
            # Get instrument info
            instrument_info = await self.get_instruments_info(symbol)
            
            # Extract validation rules from instrument info
            # This would contain min/max quantities, price increments, etc.
            
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "adjusted_quantity": quantity,
                "adjusted_price": price
            }
            
            # Add validation logic here based on instrument specifications
            # For now, basic validation
            try:
                qty_float = float(quantity)
                if qty_float <= 0:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Quantity must be positive")
            except ValueError:
                validation_result["valid"] = False
                validation_result["errors"].append("Invalid quantity format")
            
            if price:
                try:
                    price_float = float(price)
                    if price_float <= 0:
                        validation_result["valid"] = False
                        validation_result["errors"].append("Price must be positive")
                except ValueError:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Invalid price format")
            
            return validation_result
            
        except Exception as e:
            logger.error("Failed to validate order parameters", error=str(e))
            return {
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": []
            }
