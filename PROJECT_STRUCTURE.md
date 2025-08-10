# Claude Trading Orchestrator - Project Structure

## Clean, Simple Structure

```
claude-trading-orchestrator/
├── README.md                    # Main documentation
├── setup.py                     # Package installation
├── requirements.txt             # Dependencies (4 packages only)
├── config/
│   └── claude_trader.yaml      # Trading configuration
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── claude_orchestrator.py  # Main orchestrator logic
│   └── cli/
│       ├── __init__.py
│       └── claude_cli.py        # CLI interface
└── venv/                        # Virtual environment
```

## Key Files

### Core Components
- **`src/core/claude_orchestrator.py`**: Main orchestrator that wraps Claude CLI
- **`src/cli/claude_cli.py`**: CLI interface with typer and rich
- **`config/claude_trader.yaml`**: Configuration file for trading preferences

### Configuration
- **Trading styles**: aggressive, moderate, cautious, conservative
- **Configurable coins**: Any cryptocurrency symbols
- **Monitoring intervals**: 1-60 minutes
- **Position sizing**: Configurable percentage ranges

### Dependencies (Only 4!)
- **typer**: CLI framework
- **rich**: Beautiful terminal output
- **PyYAML**: Configuration file parsing
- **structlog**: Structured logging

## Commands

```bash
# Install
pip install -e .

# Configure
claude-trader config --show
claude-trader config --style aggressive --coins BTC,ETH,SOL

# Run
claude-trader start
claude-trader status
claude-trader history
```

## How It Works

1. **Loads configuration** from `config/claude_trader.yaml`
2. **Builds dynamic prompts** based on your trading style and coin preferences
3. **Executes Claude CLI** with proper environment variables
4. **Monitors trades** at configured intervals
5. **Detects completion** using configurable keywords
6. **Starts new cycles** automatically

## Environment Variables (Auto-set)

```bash
ANTHROPIC_MODEL='us.anthropic.claude-sonnet-4-20250514-v1:0'
CLAUDE_CODE_USE_BEDROCK=1
AWS_PROFILE=fintech-tax-bedrock-full-access-profile
AWS_REGION=us-west-2
```

## Clean & Simple

- **No complex trading engines**
- **No direct API integrations**
- **No risk management modules**
- **No session managers**
- **No MCP clients**

Just a clean wrapper around the Claude CLI command for 24/7 automated trading.
