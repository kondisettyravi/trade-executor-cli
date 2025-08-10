# Trade Executor CLI

An intelligent, automated cryptocurrency trading system powered by AWS Bedrock LLM that executes and manages trades on Bybit exchange with sophisticated risk management and real-time monitoring.

## 🚀 Features

- **LLM-Powered Decision Making**: Uses AWS Bedrock (Claude 3.5 Sonnet/Claude 4) for intelligent trading decisions
- **Automated Trading**: One trade per session with continuous monitoring and management
- **Risk Management**: Comprehensive risk controls with position sizing, stop losses, and daily limits
- **Real-time Monitoring**: Live dashboard with market data, trade status, and performance metrics
- **News Integration**: Hourly news analysis to inform trading decisions (extensible via MCP)
- **Professional CLI**: Beautiful command-line interface with rich formatting and progress indicators
- **Session Management**: Complete trade history and performance analytics
- **Emergency Controls**: Immediate position closure and risk management triggers

## 📋 Prerequisites

- Python 3.9 or higher
- AWS Account with Bedrock access
- Bybit account with API credentials
- Minimum $50 account balance recommended

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/trade-executor-cli.git
cd trade-executor-cli
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install the CLI Tool

```bash
pip install -e .
```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# Bybit API Credentials
BYBIT_API_KEY=your_bybit_api_key
BYBIT_API_SECRET=your_bybit_api_secret

# AWS Credentials (choose one method)
# Method 1: AWS Profile (recommended for production)
AWS_PROFILE=your_aws_profile_name

# Method 2: Direct AWS credentials
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Method 3: Bedrock API Key (recommended for development/testing)
AWS_BEARER_TOKEN_BEDROCK=your_bedrock_api_key
```

### 2. Configuration File

The main configuration is in `config/settings.yaml`. Key settings include:

```yaml
trading:
  position_sizes: [5, 10, 15, 20, 25]  # Percentage of balance
  max_daily_loss_percent: 10
  max_position_loss_percent: 5
  price_check_interval_minutes: 15
  news_check_interval_minutes: 60
  allowed_pairs: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "DOTUSDT"]

bedrock:
  region: "us-east-1"
  model_id: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  temperature: 0.1

bybit:
  testnet: false
  category: "spot"
```

### 3. AWS Bedrock Setup

#### Option A: Bedrock API Key (Recommended for Development)

1. **Generate API Key**:
   ```bash
   trade-executor setup-bedrock
   ```
   This command provides a step-by-step guide to generate a 30-day Bedrock API key.

2. **Configure**:
   - Add `AWS_BEARER_TOKEN_BEDROCK=your_api_key` to `.env`
   - Set `use_api_key: true` in `config/settings.yaml`

#### Option B: AWS Profile (Recommended for Production)

1. Configure AWS CLI with your profile
2. Set `AWS_PROFILE=your_profile_name` in `.env`
3. Keep `use_api_key: false` in `config/settings.yaml`

### 4. Validate Configuration

```bash
trade-executor config --validate
```

## 🎯 Usage

### Start Trading Session

```bash
# Start automated trading (demo mode enabled by default)
trade-executor start

# Start in paper trading mode (no real trades)
trade-executor start --paper

# Use Bybit MCP demo mode (safe testing with realistic data)
trade-executor start --demo

# Use live trading mode (real money - be careful!)
trade-executor start --live

# Start with verbose logging
trade-executor start --verbose
```

### Monitor Trading

```bash
# Launch live dashboard
trade-executor dashboard

# Check current status
trade-executor status

# View trading history
trade-executor history --limit 20
```

### Stop Trading

```bash
# Stop gracefully (closes positions safely)
trade-executor stop

# Emergency stop (immediate position closure)
trade-executor stop --emergency
```

### Performance Analytics

```bash
# View performance summary
trade-executor performance --days 30

# Show configuration
trade-executor config --show
```

## 📊 Dashboard

The live dashboard provides real-time monitoring with:

- **Session Information**: Current session status and details
- **Active Trade**: Real-time trade monitoring with P&L
- **Risk Status**: Current risk levels and limits
- **Market Data**: Live price feeds for all trading pairs
- **News Sentiment**: Latest news analysis and market sentiment
- **Performance Metrics**: Win rate, P&L, and trade statistics

Launch with: `trade-executor dashboard`

## 🛡️ Risk Management

The system includes comprehensive risk management:

### Position Sizing
- LLM chooses from 5%, 10%, 15%, 20%, or 25% of available balance
- Minimum $10 position size
- Dynamic sizing based on market conditions and risk assessment

### Stop Loss Management
- Mandatory stop losses on all trades
- Maximum 5% loss per position
- Emergency stop at 15% loss
- Automatic adjustment based on market conditions

### Daily Limits
- Maximum 3 trades per day
- Maximum 10% daily loss limit
- 30-minute cooldown between trades
- Automatic session termination on limit breach

### Emergency Controls
- Immediate position closure capability
- Risk event logging and monitoring
- Automatic emergency stops on critical conditions

## 🔧 Architecture

### Core Components

- **Trading Engine**: Main orchestrator managing the trading lifecycle
- **LLM Decision Maker**: AWS Bedrock integration for intelligent decisions
- **Bybit Client**: Exchange integration via MCP server
- **Risk Manager**: Comprehensive risk control system
- **Session Manager**: Trade history and performance tracking
- **CLI Interface**: Professional command-line interface

### Data Flow

1. **Market Analysis**: Continuous monitoring of price data and market conditions
2. **News Integration**: Hourly news analysis for market sentiment
3. **Decision Making**: LLM analyzes all data to make trading decisions
4. **Risk Validation**: All trades validated against risk parameters
5. **Execution**: Orders placed via Bybit MCP integration
6. **Monitoring**: 15-minute intervals for position evaluation
7. **Management**: Dynamic stop loss and take profit adjustments

## 🔌 MCP Integration

The system uses Model Context Protocol (MCP) for:

- **Bybit Integration**: Trading operations via MCP server
- **News Sources**: Extensible news integration (future)
- **Market Data**: Real-time price and volume data
- **Analytics**: Performance and risk metrics

### Available MCP Tools

- `get_wallet_balance`: Account balance information
- `get_market_data`: Real-time market data
- `place_order`: Execute trading orders
- `get_positions`: Current position status
- `cancel_order`: Order cancellation
- `get_order_history`: Historical trade data

## 📈 Trading Strategies

The LLM dynamically selects strategies based on market conditions:

- **Trend Following**: Momentum-based entries
- **Mean Reversion**: Counter-trend opportunities
- **Breakout Trading**: Range breakout strategies
- **News-Driven**: Sentiment-based decisions
- **Risk-Adjusted**: Dynamic position sizing

## 🔍 Monitoring and Logging

### Structured Logging
- Comprehensive logging with structured data
- Trade decision reasoning captured
- Risk events and alerts logged
- Performance metrics tracked

### Database Storage
- SQLite database for trade history
- Session management and analytics
- Risk event logging
- Performance metrics storage

### Real-time Monitoring
- Live dashboard updates every 5 seconds
- Position monitoring every 15 minutes
- News updates every hour
- Risk status continuous monitoring

## 🚨 Safety Features

### Paper Trading Mode
Test the system without real money:
```bash
trade-executor start --paper
```

### Emergency Stops
- Manual emergency stop: `trade-executor stop --emergency`
- Automatic emergency stops on risk limit breach
- Immediate position closure capability

### Configuration Validation
- Startup configuration validation
- API credential verification
- Risk parameter validation

## 📝 Example Session

```bash
# 1. Validate setup
trade-executor config --validate

# 2. Start trading session
trade-executor start

# 3. Monitor in real-time
trade-executor dashboard

# 4. Check performance
trade-executor performance

# 5. Stop when done
trade-executor stop
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## ⚠️ Disclaimer

This software is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. The authors are not responsible for any financial losses incurred through the use of this software. Always:

- Start with small amounts
- Use paper trading mode first
- Understand the risks involved
- Never invest more than you can afford to lose
- Comply with local regulations

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the documentation
2. Review existing GitHub issues
3. Create a new issue with detailed information
4. Include logs and configuration (remove sensitive data)

## 🔮 Roadmap

- [ ] Additional exchange integrations
- [ ] More sophisticated trading strategies
- [ ] Advanced risk management features
- [ ] Web-based dashboard
- [ ] Mobile notifications
- [ ] Backtesting capabilities
- [ ] Portfolio management features
- [ ] Social trading integration

---

**Happy Trading! 🚀**

*Remember: The best trade is sometimes no trade. Let the LLM make the decisions, but always maintain proper risk management.*
