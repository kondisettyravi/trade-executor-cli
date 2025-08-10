# Trade Executor CLI - Project Structure

## Overview
This is a comprehensive automated cryptocurrency trading system powered by AWS Bedrock LLM with sophisticated risk management and real-time monitoring capabilities.

## Project Structure

```
trade-executor-cli/
├── README.md                          # Comprehensive documentation
├── PROJECT_STRUCTURE.md               # This file
├── setup.py                          # Package installation configuration
├── requirements.txt                   # Python dependencies
├── install.sh                        # Automated installation script
├── .env.example                      # Environment variables template
│
├── config/
│   └── settings.yaml                 # Main configuration file
│
├── src/                              # Main source code
│   ├── __init__.py                   # Package initialization
│   │
│   ├── core/                         # Core trading engine
│   │   ├── __init__.py
│   │   ├── config.py                 # Configuration management
│   │   ├── trading_engine.py         # Main trading orchestrator
│   │   └── session_manager.py        # Session and trade history management
│   │
│   ├── integrations/                 # External service integrations
│   │   ├── __init__.py
│   │   ├── bedrock_client.py         # AWS Bedrock LLM integration
│   │   ├── bybit_client.py           # Bybit exchange integration
│   │   └── mcp_client.py             # MCP server communication
│   │
│   ├── risk/                         # Risk management system
│   │   ├── __init__.py
│   │   └── risk_manager.py           # Comprehensive risk controls
│   │
│   └── cli/                          # Command-line interface
│       ├── __init__.py
│       ├── main.py                   # Main CLI application
│       └── dashboard.py              # Live trading dashboard
│
├── data/                             # Generated at runtime
│   └── trades.db                     # SQLite database for trade history
│
└── logs/                             # Generated at runtime
    └── trading.log                   # Application logs
```

## Key Components

### 1. Core Trading Engine (`src/core/`)

#### `trading_engine.py`
- **Main orchestrator** managing the entire trading lifecycle
- **Session management** with one-trade-per-session approach
- **Market analysis** using LLM for intelligent decision making
- **Automated monitoring** every 15 minutes
- **News integration** every hour for informed decisions
- **Risk validation** before every trade
- **Position management** with dynamic adjustments

#### `config.py`
- **Centralized configuration** management using Pydantic
- **Environment variable** integration
- **YAML configuration** file support
- **Validation** of all settings
- **Type safety** with proper data models

#### `session_manager.py`
- **SQLite database** integration for persistence
- **Trade history** tracking and analytics
- **Performance metrics** calculation
- **Session lifecycle** management
- **Risk event** logging

### 2. Integrations (`src/integrations/`)

#### `bedrock_client.py`
- **AWS Bedrock** integration for LLM capabilities
- **Claude 3.5 Sonnet/Claude 4** model support
- **Intelligent prompts** for market analysis and trading decisions
- **Fallback models** for reliability
- **Structured responses** with JSON parsing

#### `bybit_client.py`
- **Bybit exchange** integration via MCP
- **Comprehensive API** coverage (orders, positions, market data)
- **Position sizing** calculations
- **Order validation** and error handling
- **Real-time market data** retrieval

#### `mcp_client.py`
- **Model Context Protocol** integration
- **Extensible architecture** for multiple MCP servers
- **Mock data support** for development/testing
- **Error handling** and fallback mechanisms

### 3. Risk Management (`src/risk/`)

#### `risk_manager.py`
- **Position sizing** validation (5-25% of balance)
- **Daily limits** (max 3 trades, 10% daily loss)
- **Stop loss** requirements and validation
- **Emergency stops** at 15% loss
- **Cooldown periods** between trades
- **Real-time monitoring** of position risk

### 4. CLI Interface (`src/cli/`)

#### `main.py`
- **Professional CLI** using Typer and Rich
- **Command structure** with intuitive subcommands
- **Progress indicators** and status updates
- **Error handling** with user-friendly messages
- **Configuration management** commands

#### `dashboard.py`
- **Live dashboard** with real-time updates
- **Rich terminal UI** with panels and tables
- **Market data** visualization
- **Trade monitoring** with P&L tracking
- **Risk status** indicators
- **Performance metrics** display

## Data Flow

### 1. Initialization
```
CLI Start → Config Validation → MCP Connection → Trading Engine Init
```

### 2. Trading Session
```
Session Start → Market Analysis → LLM Decision → Risk Validation → Order Execution
```

### 3. Monitoring Loop
```
Position Check → Market Data → LLM Evaluation → Action Decision → Risk Assessment
```

### 4. News Integration
```
News Fetch → Sentiment Analysis → LLM Context Update → Strategy Adjustment
```

## Key Features

### 🤖 **LLM-Powered Intelligence**
- Market condition analysis
- Dynamic strategy selection
- Risk-adjusted position sizing
- News sentiment integration
- Adaptive decision making

### 🛡️ **Comprehensive Risk Management**
- Multi-layer risk controls
- Real-time position monitoring
- Emergency stop mechanisms
- Daily and position limits
- Automated risk assessment

### 📊 **Professional Monitoring**
- Live dashboard with real-time updates
- Comprehensive trade history
- Performance analytics
- Risk status indicators
- Market data visualization

### 🔧 **Robust Architecture**
- Modular design for extensibility
- Error handling and recovery
- Configuration management
- Logging and debugging
- Database persistence

## Installation & Usage

### Quick Start
```bash
# Clone and install
git clone <repository>
cd trade-executor-cli
chmod +x install.sh
./install.sh

# Configure
cp .env.example .env
# Edit .env with your API keys

# Validate setup
trade-executor config --validate

# Start trading (paper mode first!)
trade-executor start --paper

# Monitor with dashboard
trade-executor dashboard
```

### Commands
- `trade-executor start` - Start automated trading
- `trade-executor stop` - Stop trading session
- `trade-executor status` - Show current status
- `trade-executor dashboard` - Live monitoring
- `trade-executor history` - Trade history
- `trade-executor performance` - Analytics
- `trade-executor config` - Configuration management

## Safety Features

### 🧪 **Testing & Development**
- Paper trading mode
- Mock MCP data for development
- Configuration validation
- Comprehensive error handling

### 🚨 **Emergency Controls**
- Manual emergency stop
- Automatic risk triggers
- Position closure mechanisms
- Daily loss limits

### 📝 **Monitoring & Logging**
- Structured logging
- Trade decision reasoning
- Risk event tracking
- Performance metrics

## Extensibility

The system is designed for easy extension:

### **New Exchanges**
- Implement new client in `src/integrations/`
- Add MCP server integration
- Update configuration

### **Additional Strategies**
- Add strategy modules in `src/strategies/`
- Integrate with LLM decision making
- Update prompts and logic

### **News Sources**
- Add news MCP servers
- Implement sentiment analysis
- Integrate with decision making

### **Risk Controls**
- Extend risk manager
- Add new validation rules
- Implement custom limits

## Development Notes

### **Code Quality**
- Type hints throughout
- Comprehensive error handling
- Structured logging
- Modular architecture

### **Testing**
- Mock data for development
- Paper trading mode
- Configuration validation
- Error simulation

### **Documentation**
- Comprehensive README
- Code comments
- Type annotations
- Usage examples

This architecture provides a solid foundation for automated cryptocurrency trading with LLM intelligence, comprehensive risk management, and professional monitoring capabilities.
