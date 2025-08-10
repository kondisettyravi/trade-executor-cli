# Claude Trading Orchestrator

A 24/7 automated trading system that uses the Claude CLI command for all trading decisions and monitoring. This orchestrator acts as a wrapper around your existing `claude` command to provide continuous, autonomous trading.

## Overview

The Claude Trading Orchestrator is designed to:

1. **Invoke Claude** to take initial trades using Bybit and News MCPs
2. **Monitor trades** every 15 minutes by calling Claude again
3. **Continue monitoring** until Claude decides to close the trade
4. **Start new trades** automatically after completion
5. **Run 24/7** like you're watching markets constantly

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Claude Trading Orchestrator                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Initial   │    │  Monitor    │    │   Close     │     │
│  │   Trade     │───▶│   Trade     │───▶│   Trade     │     │
│  │             │    │ (15 mins)   │    │             │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  ┌─────────────────────────────────────────────────────────┤
│  │            Claude CLI Command                           │
│  │  claude -p "trading prompt..."                         │
│  │  claude -p -c "monitor the trade"                      │
│  └─────────────────────────────────────────────────────────┤
│                           │                                │
│                           ▼                                │
│  ┌─────────────────────────────────────────────────────────┤
│  │              MCP Servers                               │
│  │  • Bybit MCP (trading)                                │
│  │  • News MCP (market sentiment)                        │
│  └─────────────────────────────────────────────────────────┘
```

## Installation

1. **Install the package:**
   ```bash
   source venv/bin/activate
   pip install -e .
   ```

2. **Set up Claude environment variables:**
   ```bash
   export ANTHROPIC_MODEL='us.anthropic.claude-sonnet-4-20250514-v1:0'
   export CLAUDE_CODE_USE_BEDROCK=1
   export AWS_PROFILE=fintech-tax-bedrock-full-access-profile
   export AWS_REGION=us-west-2
   ```

3. **Verify installation:**
   ```bash
   claude-trader --help
   ```

## Usage

### Start 24/7 Trading

Start the orchestrator to run continuously:

```bash
claude-trader start
```

With custom monitoring interval:
```bash
claude-trader start --interval 10  # Monitor every 10 minutes
```

### Monitor Status

Check the current status:
```bash
claude-trader status
```

### Test Claude Integration

Test if Claude CLI is working:
```bash
claude-trader test
```

### Simulate Trading Cycles

Test the orchestrator with simulation:
```bash
claude-trader simulate --cycles 3
```

### View Trading History

See completed trades:
```bash
claude-trader history --limit 10
```

## How It Works

### 1. Trade Initiation

When no active trade exists, the orchestrator calls:

```bash
claude --dangerously-skip-permissions -p "I would like to use the bybit mcp server and take a profitable trade on the major crypto currencies such as BTC, ETH, SOL, XRP and DOGE. I want the trade to be profitable and would want to monitor the trade and set the stop loss such that we don't get losses. Monitor the trade every 15 minutes. Be the boss. Take the right decision. You know that you are a very aggressive and profitable trader. Choose position size between 5-25% of available balance."
```

### 2. Trade Monitoring

Every 15 minutes (or your configured interval), the orchestrator calls:

```bash
claude --dangerously-skip-permissions -p -c "monitor the trade"
```

## ⚠️ Uninterrupted Execution

The orchestrator uses `--dangerously-skip-permissions` to enable uninterrupted Claude execution:

- **Benefit**: Claude can complete complex trading workflows without permission interruptions
- **Risk**: Claude has unrestricted command execution capabilities
- **Safety**: Use in isolated environments with proper data backups
- **Ideal for**: Automated trading where human intervention defeats the purpose

### 3. Trade Completion

The orchestrator detects when Claude indicates the trade is complete by looking for phrases like:
- "trade completed"
- "position closed"
- "trade closed"
- "final profit"
- "final loss"

### 4. New Cycle

After trade completion, the orchestrator automatically starts a new trade cycle.

## Configuration

### Monitoring Interval

Default: 15 minutes
```bash
claude-trader start --interval 15
```

### Claude Command Path

The orchestrator expects the `claude` command to be available in your PATH. Make sure you can run:
```bash
claude --help
```

### Working Directory

The orchestrator runs Claude commands from your current working directory:
```
/Users/rkondis/personalwork/trade-executor-cli
```

## Example Output

### Successful Trade Initiation
```
🎯 Initiating new trade with Claude
🔧 Executing claude command: claude -p "I would like to use the bybit mcp server..."
✅ Claude command executed successfully (response_length=1247)
📋 Trade initiation analysis (indicators_found=5, success=True)
✅ New trade initiated successfully
```

### Trade Monitoring
```
👁️ Monitoring current trade with Claude
🔧 Executing claude command: claude -p -c "monitor the trade"
✅ Claude command executed successfully (response_length=892)
📊 Trade monitoring update received
```

### Trade Completion
```
👁️ Monitoring current trade with Claude
🔧 Executing claude command: claude -p -c "monitor the trade"
✅ Claude command executed successfully (response_length=654)
🏁 Trade completion detected (indicator=trade completed)
🎉 Trade completed successfully
📈 Trade completed and archived (total_trades=1)
```

## Status Information

The orchestrator tracks:

- **Running Status**: Whether the orchestrator is active
- **Current Trade**: Details of active trade if any
- **Trade History**: All completed trades
- **Monitoring Interval**: How often trades are monitored
- **Last Activity**: Timestamp of last action

## Error Handling

The orchestrator handles:

- **Claude Command Failures**: Logs errors and retries in next cycle
- **Trade Parsing Errors**: Continues monitoring if parsing fails
- **Network Issues**: Robust error handling with retries
- **Keyboard Interrupts**: Graceful shutdown

## Logging

All activities are logged with structured logging:

```
2025-08-10 20:07:31 [info] 🚀 Starting 24/7 Claude Trading Orchestrator
2025-08-10 20:07:31 [info] 🎯 Initiating new trade with Claude
2025-08-10 20:07:32 [info] ✅ New trade initiated successfully
2025-08-10 20:22:32 [info] 👁️ Monitoring current trade with Claude
2025-08-10 20:22:33 [info] 📊 Trade monitoring update received
```

## Safety Features

- **Demo Mode**: Works with Bybit MCP demo mode for safe testing
- **Error Recovery**: Continues operation despite individual failures
- **Graceful Shutdown**: Ctrl+C stops orchestrator cleanly
- **Trade Validation**: Parses Claude responses to ensure trades are valid

## Troubleshooting

### Claude Command Not Found
```bash
# Make sure claude is in your PATH
which claude
# If not found, install or add to PATH
```

### Permission Errors
```bash
# Make sure the working directory is accessible
cd /Users/rkondis/personalwork/trade-executor-cli
ls -la
```

### MCP Server Issues
```bash
# Test your MCP servers separately
claude -p "test bybit connection"
```

## Advanced Usage

### Custom Prompts

You can modify the trading prompts in `src/core/claude_orchestrator.py`:

```python
# Aggressive trading prompt
prompt = (
    "I would like to use the bybit mcp server and take a profitable trade..."
)
```

### Custom Completion Detection

Modify the completion indicators:

```python
completion_indicators = [
    "trade completed",
    "position closed",
    "custom completion phrase"
]
```

## Integration with Existing System

The orchestrator works alongside your existing trade-executor CLI:

- **claude-trader**: 24/7 orchestrator using Claude CLI
- **trade-executor**: Direct LLM integration system

Both can be used independently or together for different trading strategies.

## Performance

- **Memory Usage**: Minimal, only stores trade history
- **CPU Usage**: Low, mostly waiting between cycles
- **Network Usage**: Only during Claude CLI calls
- **Disk Usage**: Logs and trade history only

## Future Enhancements

- **Multiple Strategies**: Support different trading prompts
- **Risk Management**: Position sizing controls
- **Performance Analytics**: Detailed trade analysis
- **Web Dashboard**: Real-time monitoring interface
- **Notifications**: Alerts for trade events

## Support

For issues or questions:

1. Check the logs for error messages
2. Test Claude CLI integration with `claude-trader test`
3. Verify MCP servers are working
4. Check system requirements and permissions

## License

MIT License - see LICENSE file for details.
