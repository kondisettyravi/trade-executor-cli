"""
Bybit Client - Wrapper around MCP Bybit server for trading operations
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BybitClient:
    def __init__(self, mcp_client):
        """
        Initialize Bybit client with MCP connection
        
        Args:
            mcp_client: MCP client instance for tool execution
        """
        self.mcp_client = mcp_client
        self.category = "spot"  # Default to spot trading
        
    async def get_wallet_balance(self, account_type: str = "UNIFIED", coin: Optional[str] = None) -> Dict:
        """Get wallet balance"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_wallet_balance",
                arguments={
                    "accountType": account_type,
                    "coin": coin
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            raise
    
    async def get_ticker(self, symbol: str) -> Dict:
        """Get ticker information for a symbol"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_tickers",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            raise
    
    async def get_kline_data(self, symbol: str, interval: str, limit: int = 200, 
                           start: Optional[int] = None, end: Optional[int] = None) -> Dict:
        """Get K-line (candlestick) data"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_kline",
                arguments={
                    "category": self.category,
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit,
                    "start": start,
                    "end": end
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting kline data for {symbol}: {e}")
            raise
    
    async def get_orderbook(self, symbol: str, limit: int = 50) -> Dict:
        """Get orderbook data"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_orderbook",
                arguments={
                    "category": self.category,
                    "symbol": symbol,
                    "limit": limit
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            raise
    
    async def place_order(self, symbol: str, side: str, order_type: str, qty: str,
                         price: Optional[str] = None, take_profit: Optional[str] = None,
                         stop_loss: Optional[str] = None, time_in_force: str = "GTC") -> Dict:
        """Place an order"""
        try:
            order_args = {
                "category": self.category,
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": qty,
                "timeInForce": time_in_force
            }
            
            if price:
                order_args["price"] = price
            if take_profit:
                order_args["takeProfit"] = take_profit
                order_args["tpOrderType"] = "Market"
            if stop_loss:
                order_args["stopLoss"] = stop_loss
                order_args["slOrderType"] = "Market"
            
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="place_order",
                arguments=order_args
            )
            
            logger.info(f"Order placed: {side} {qty} {symbol} at {price or 'market'}")
            return result
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: Optional[str] = None, 
                          order_link_id: Optional[str] = None) -> Dict:
        """Cancel an order"""
        try:
            cancel_args = {
                "category": self.category,
                "symbol": symbol
            }
            
            if order_id:
                cancel_args["orderId"] = order_id
            if order_link_id:
                cancel_args["orderLinkId"] = order_link_id
            
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="cancel_order",
                arguments=cancel_args
            )
            
            logger.info(f"Order cancelled: {order_id or order_link_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            raise
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> Dict:
        """Get open orders"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_open_orders",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            raise
    
    async def get_positions(self, symbol: Optional[str] = None) -> Dict:
        """Get position information"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_positions",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise
    
    async def set_trading_stop(self, symbol: str, take_profit: Optional[str] = None,
                              stop_loss: Optional[str] = None, trailing_stop: Optional[str] = None) -> Dict:
        """Set trading stop (TP/SL)"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="set_trading_stop",
                arguments={
                    "category": self.category,
                    "symbol": symbol,
                    "takeProfit": take_profit,
                    "stopLoss": stop_loss,
                    "trailingStop": trailing_stop
                }
            )
            
            logger.info(f"Trading stop set for {symbol}: TP={take_profit}, SL={stop_loss}")
            return result
            
        except Exception as e:
            logger.error(f"Error setting trading stop: {e}")
            raise
    
    async def get_account_info(self) -> Dict:
        """Get API key information"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_api_key_information",
                arguments={}
            )
            return result
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise
    
    async def get_instrument_info(self, symbol: str) -> Dict:
        """Get instrument information"""
        try:
            result = await self.mcp_client.use_mcp_tool(
                server_name="bybit",
                tool_name="get_instruments_info",
                arguments={
                    "category": self.category,
                    "symbol": symbol
                }
            )
            return result
        except Exception as e:
            logger.error(f"Error getting instrument info for {symbol}: {e}")
            raise
    
    def calculate_position_size(self, balance: float, risk_per_trade: float, 
                               entry_price: float, stop_loss_price: float) -> float:
        """Calculate position size based on risk management"""
        try:
            risk_amount = balance * risk_per_trade
            price_diff = abs(entry_price - stop_loss_price)
            position_size = risk_amount / price_diff
            
            logger.info(f"Position size calculated: {position_size:.6f}")
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def format_quantity(self, quantity: float, symbol: str) -> str:
        """Format quantity according to symbol requirements"""
        # For BTC pairs, limit to 6 decimal places
        if "BTC" in symbol:
            return f"{quantity:.6f}"
        # For other pairs, use appropriate precision
        elif "ETH" in symbol:
            return f"{quantity:.5f}"
        else:
            return f"{quantity:.4f}"
    
    def format_price(self, price: float, symbol: str) -> str:
        """Format price according to symbol requirements"""
        # Most USDT pairs use 2-4 decimal places for price
        if "USDT" in symbol:
            return f"{price:.2f}"
        else:
            return f"{price:.4f}"
