# Crypto Trading Bot

An automated cryptocurrency trading application that uses Claude Code for analysis and Bybit MCP server for trading operations.

## Features

- **Automated Trading**: Fully automated trading with minimal human intervention
- **Claude Code Integration**: Uses Claude Code for sophisticated trading analysis
- **Bybit MCP Integration**: Leverages advanced Bybit MCP tools for:
  - Trending coin detection
  - Multi-timeframe momentum analysis
  - Technical indicators (RSI, MACD, Bollinger Bands)
  - Position sizing and risk management
  - Order execution and monitoring
- **Risk Management**: Professional-grade risk management with dynamic TP/SL adjustments
- **Fresh Analysis**: Each trade starts with a clean Claude Code session
- **Comprehensive Logging**: Real-time logging and monitoring

## Architecture

The application consists of several key components:

1. **main.py** - Main trading orchestrator
2. **mcp_client.py** - MCP client integration for Bybit tools
3. **config.json** - Configuration file for trading parameters
4. **claude_interface.py** - Claude Code interface (legacy, replaced by direct integration)
5. **bybit_client.py** - Bybit client wrapper (legacy, replaced by MCP tools)

## Trading Flow

1. **Coin Selection**: Uses `get_trending_coins` MCP tool to find high-momentum coins
2. **Analysis**: Creates a Claude Code session that uses multiple MCP tools:
   - `scan_multi_timeframe_momentum` - Multi-timeframe trend analysis
   - `calculate_rsi` - RSI indicator analysis
   - `calculate_macd` - MACD crossover signals
   - `calculate_bollinger_bands` - Bollinger Bands analysis
3. **Decision Making**: Combines all signals to make trading decisions
4. **Execution**: Uses MCP tools to:
   - Calculate optimal position size
   - Place orders with TP/SL
5. **Monitoring**: Continuously monitors position and adjusts TP/SL using Claude Code
6. **Completion**: Closes position and starts new cycle with fresh analysis

## Configuration

Edit `config.json` to customize:

```json
{
  "trading": {
    "coins": ["BTCUSDT", "ETHUSDT", "SOLUSDT", ...],
    "risk_per_trade": 0.02,
    "max_concurrent_positions": 1,
    "risk_reward_ratio": 2.0
  },
  "technical_analysis": {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9
  }
}
```

## Prerequisites

1. **Claude Code**: Install and configure Claude Code CLI
2. **Bybit MCP Server**: Ensure Bybit MCP server is running and configured
3. **Python Dependencies**: Install required packages

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python main.py
```

### Test MCP Integration

```bash
python test_mcp.py
```

## MCP Tools Used

The application leverages these advanced Bybit MCP tools:

- `get_trending_coins` - Find high-momentum coins
- `calculate_rsi` - RSI analysis with signals
- `calculate_macd` - MACD analysis with crossovers
- `calculate_bollinger_bands` - Bollinger Bands analysis
- `scan_multi_timeframe_momentum` - Multi-timeframe analysis
- `get_tickers` - Real-time price data
- `get_wallet_balance` - Account balance
- `calculate_position_size` - Risk-based position sizing
- `place_order` - Order execution
- `get_positions` - Position monitoring
- `set_trading_stop` - TP/SL adjustments
- `cancel_order` - Order cancellation

## Risk Management

- **Position Sizing**: Risk 2% of account per trade
- **Stop Loss**: Dynamic stop loss based on ATR
- **Take Profit**: 2:1 risk-reward ratio
- **Trailing Stops**: Move to breakeven at 2% profit
- **Maximum Positions**: 1 concurrent position

## Logging

All trading activity is logged to:
- `trading.log` - File logging
- Console output - Real-time monitoring

## Safety Features

- **Error Handling**: Comprehensive error handling and recovery
- **Position Limits**: Maximum 1 concurrent position
- **Timeout Protection**: Claude Code execution timeouts
- **Fallback Logic**: Fallback to config coins if trending detection fails

## Development

### Adding New Indicators

1. Add MCP tool call in `create_analysis_script()`
2. Update signal analysis logic
3. Test with `test_mcp.py`

### Customizing Strategy

1. Modify signal combination logic in Claude Code scripts
2. Adjust confidence thresholds
3. Update risk management parameters

## Disclaimer

This is a trading bot that can result in financial losses. Use at your own risk and ensure you understand the risks involved in cryptocurrency trading.

## License

MIT License - see LICENSE file for details.
