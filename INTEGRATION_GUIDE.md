# MCP Integration Guide

This guide explains how to integrate the trading bot with real Bybit MCP tools.

## Current Implementation

The trading bot is currently set up with a hybrid approach:
- **Mock MCP calls** for demonstration and testing
- **Real MCP integration points** ready for actual implementation

## File Structure

```
trade-executor-cli/
├── main.py                 # Main trading orchestrator
├── mcp_client.py          # MCP client integration layer
├── config.json            # Trading configuration
├── run_bot.py             # Bot launcher script
├── test_mcp.py            # MCP integration tests
├── requirements.txt       # Python dependencies
├── README.md              # Main documentation
├── INTEGRATION_GUIDE.md   # This file
├── claude_interface.py    # Legacy Claude Code interface
└── bybit_client.py        # Legacy Bybit wrapper
```

## Real MCP Integration

To integrate with actual Bybit MCP tools, modify `mcp_client.py`:

### Step 1: Replace Mock Calls

In `mcp_client.py`, replace the `_call_real_mcp_tool` method:

```python
async def _call_real_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call real MCP tool using Cline's MCP infrastructure"""
    
    # Use Cline's MCP system to make actual calls
    # This would integrate with the actual MCP client
    
    # Example of how this might look:
    from cline_mcp import use_mcp_tool as cline_mcp_tool
    
    try:
        result = await cline_mcp_tool(
            server_name=self.server_name,
            tool_name=tool_name,
            arguments=arguments
        )
        return result
    except Exception as e:
        logger.error(f"Real MCP call failed: {e}")
        raise
```

### Step 2: Update Tool Mapping

Ensure all tools are mapped to real MCP calls:

```python
# In _call_real_mcp_tool method
REAL_MCP_TOOLS = [
    "get_trending_coins",
    "calculate_rsi", 
    "scan_multi_timeframe_momentum",
    "calculate_macd",
    "calculate_bollinger_bands",
    "get_tickers",
    "get_wallet_balance",
    "calculate_position_size",
    "place_order",
    "get_positions",
    "set_trading_stop",
    "cancel_order"
]

if tool_name in REAL_MCP_TOOLS:
    return await self._make_actual_mcp_call(tool_name, arguments)
```

## Claude Code Integration

The bot creates Python scripts that are executed in Claude Code environment. To enable real MCP calls in Claude Code:

### Update Analysis Script

In `main.py`, modify `create_analysis_script()` to use real MCP calls:

```python
def create_analysis_script(self, symbol: str) -> str:
    script = f'''
import json
import asyncio
from datetime import datetime

# Import actual MCP client in Claude Code environment
from mcp_integration import use_mcp_tool

async def analyze_trading_opportunity():
    """Analysis using real MCP tools"""
    symbol = "{symbol}"
    
    # Real MCP calls
    momentum_result = await use_mcp_tool("bybit", "scan_multi_timeframe_momentum", {{
        "category": "spot",
        "symbol": symbol,
        "timeframes": ["15", "60", "240", "D"],
        "limit": 50
    }})
    
    # ... rest of analysis logic
'''
```

## Testing Integration

### Test Real MCP Calls

1. **Run MCP Tests**:
   ```bash
   python test_mcp.py
   ```

2. **Test Individual Tools**:
   ```python
   # Test trending coins
   result = await use_mcp_tool("bybit", "get_trending_coins", {
       "category": "spot",
       "limit": 10
   })
   ```

3. **Test Complete Workflow**:
   ```bash
   python run_bot.py
   ```

## Configuration for Real Trading

### Update config.json

```json
{
  "trading": {
    "coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
    "risk_per_trade": 0.01,  // 1% risk for real trading
    "max_concurrent_positions": 1,
    "risk_reward_ratio": 2.0
  },
  "bybit": {
    "category": "spot",
    "account_type": "UNIFIED",
    "testnet": false  // Set to true for testing
  }
}
```

### Environment Variables

Set up required environment variables:

```bash
export BYBIT_API_KEY="your_api_key"
export BYBIT_SECRET_KEY="your_secret_key"
export CLAUDE_CODE_API_KEY="your_claude_code_key"
```

## Safety Measures

### 1. Paper Trading Mode

Add paper trading mode to test without real money:

```python
class TradingBot:
    def __init__(self, config_path: str = 'config.json', paper_trading: bool = True):
        self.paper_trading = paper_trading
        
    async def execute_trade(self, analysis: Dict) -> bool:
        if self.paper_trading:
            logger.info(f"PAPER TRADE: {analysis['action']} {analysis['symbol']}")
            return True
        else:
            # Real trading logic
            return await self._execute_real_trade(analysis)
```

### 2. Position Size Limits

```python
def validate_position_size(self, size: float, symbol: str) -> float:
    """Validate and limit position size"""
    max_position_value = 100  # $100 max position
    current_price = self.get_current_price(symbol)
    max_size = max_position_value / current_price
    
    return min(size, max_size)
```

### 3. Trading Hours

```python
def is_trading_hours(self) -> bool:
    """Check if within allowed trading hours"""
    from datetime import datetime, time
    
    now = datetime.now().time()
    start_time = time(9, 0)   # 9 AM
    end_time = time(17, 0)    # 5 PM
    
    return start_time <= now <= end_time
```

## Monitoring and Alerts

### Add Notifications

```python
async def send_notification(self, message: str, level: str = "INFO"):
    """Send trading notifications"""
    
    # Email notification
    if level == "ERROR":
        await self.send_email_alert(message)
    
    # Discord/Slack webhook
    await self.send_webhook_notification(message, level)
    
    # Log to file
    logger.info(f"NOTIFICATION [{level}]: {message}")
```

### Performance Tracking

```python
class PerformanceTracker:
    def __init__(self):
        self.trades = []
        self.total_pnl = 0
        
    def record_trade(self, trade_result: Dict):
        """Record trade for performance analysis"""
        self.trades.append(trade_result)
        self.total_pnl += trade_result.get('pnl', 0)
        
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        if not self.trades:
            return {}
            
        win_rate = len([t for t in self.trades if t.get('pnl', 0) > 0]) / len(self.trades)
        
        return {
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'avg_pnl_per_trade': self.total_pnl / len(self.trades)
        }
```

## Deployment

### Production Deployment

1. **Set up VPS/Cloud Server**
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   ```bash
   export TRADING_ENV=production
   export LOG_LEVEL=INFO
   ```
4. **Run with Process Manager**:
   ```bash
   # Using PM2
   pm2 start run_bot.py --name crypto-trading-bot
   
   # Using systemd
   sudo systemctl start crypto-trading-bot
   ```

### Monitoring

```bash
# Check logs
tail -f trading.log

# Monitor performance
python -c "
from main import TradingBot
bot = TradingBot()
print(bot.performance_tracker.get_stats())
"
```

## Next Steps

1. **Replace mock MCP calls** with real implementations
2. **Test with paper trading** mode
3. **Implement safety measures** and position limits
4. **Add comprehensive monitoring** and alerts
5. **Deploy to production** environment
6. **Monitor and optimize** strategy performance

## Support

For issues with MCP integration:
1. Check Bybit MCP server status
2. Verify API credentials
3. Test individual MCP tools
4. Review trading logs
5. Contact support if needed

Remember: **Always test thoroughly before using real money!**
