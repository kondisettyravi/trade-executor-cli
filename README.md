# Claude Trading Orchestrator

A simple, clean 24/7 automated trading orchestrator that uses the Claude CLI command for all trading decisions.

## What It Does

- **Invokes Claude** to take trades using your Bybit and News MCPs
- **Monitors trades** every 15 minutes (configurable)
- **Continues monitoring** until Claude closes the trade
- **Starts new trades** automatically after completion
- **Runs 24/7** like you're watching markets constantly

## Quick Start

1. **Install:**
   ```bash
   pip install -e .
   ```

2. **Configure your trading style:**
   ```bash
   claude-trader config --style aggressive --coins BTC,ETH,SOL
   ```

3. **Start 24/7 trading:**
   ```bash
   claude-trader start
   ```

## Configuration

### Trading Styles
- **aggressive**: Bold positions, maximum profits
- **moderate**: Balanced risk/reward approach  
- **cautious**: Capital preservation focused
- **conservative**: Minimal risk, strict stops

### Commands

```bash
# View current configuration
claude-trader config --show

# Change trading style
claude-trader config --style cautious

# Set coins to trade
claude-trader config --coins BTC,ETH,ADA,SOL

# Change monitoring interval
claude-trader config --interval 10

# Start 24/7 trading
claude-trader start

# Check status
claude-trader status

# View trade history
claude-trader history
```

## How It Works

1. **Trade Initiation**: Calls `claude --dangerously-skip-permissions -p "trading prompt..."` with your configured style and coins
2. **Monitoring**: Every 15 minutes calls `claude --dangerously-skip-permissions -p -c "monitor the trade"`
3. **Completion**: Detects when Claude closes the trade
4. **New Cycle**: Automatically starts next trade

## ⚠️ Safety Notice

This orchestrator uses `--dangerously-skip-permissions` to let Claude work uninterrupted until completion. This is powerful but risky:

- **Risk**: Claude can run arbitrary commands without permission prompts
- **Benefit**: Uninterrupted trading execution and monitoring
- **Recommendation**: Use in a secure, isolated environment (Docker container without internet access)
- **Data Protection**: Ensure important data is backed up before use

## Environment Setup

The orchestrator automatically sets these environment variables for Claude:

```bash
export ANTHROPIC_MODEL='us.anthropic.claude-sonnet-4-20250514-v1:0'
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_PROFILE=fintech-tax-bedrock-full-access-profile
export AWS_REGION=us-west-2
```

## Configuration File

Edit `config/claude_trader.yaml` to customize:

```yaml
trading:
  style: "aggressive"
  coins: ["BTC", "ETH", "SOL", "XRP", "DOGE"]
  position_size: {min: 5, max: 25}
  monitoring_interval: 15

styles:
  aggressive:
    description: "very aggressive and profitable trader"
    risk_tolerance: "high"
    position_preference: "larger positions for maximum profit"
```

## Requirements

- Python 3.9+
- Claude CLI command available in PATH
- Bybit MCP server configured
- News MCP server (optional)

## License

MIT License
