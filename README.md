# Claude Trading Orchestrator

🚀 **Ultra-Aggressive 24/7 Automated Futures Trading System** targeting **20% daily returns** using Claude AI with advanced MCP tools and unlimited leverage capability.

## 🎯 Core Mission

**PRIMARY OBJECTIVE: ACHIEVE 20% DAILY RETURNS ON TOTAL WALLET VALUE**

This system uses Claude AI to execute high-leverage futures trades on Bybit with advanced market analysis tools, targeting aggressive daily profit goals through systematic, data-driven trading decisions.

## ⚡ Key Features

### 🎯 **Ultra-Aggressive Trading Strategy**
- **20% Daily Target**: Clear profit objective with unlimited leverage authority
- **High Leverage Trading**: 10x-100x leverage for maximum return amplification
- **Futures Market Focus**: Linear perpetual contracts (USDT margin) for leverage capability
- **Position Isolation**: Only manages positions it creates, ignores other account activity

### 🧠 **Advanced AI-Powered Analysis**
- **Volume Profile Analysis**: Point of Control (POC) and Value Area identification
- **Market Correlation**: BTC-ETH correlation analysis and volatility ratios
- **Multi-Timeframe Momentum**: Cross-timeframe trend confirmation
- **On-Chain Metrics**: Network health and whale activity analysis
- **Dynamic Coin Selection**: Trending coins identification via MCP tools

### 🔄 **Intelligent Trade Management**
- **Real-time TP/SL Adjustment**: Dynamic profit protection and loss minimization
- **Fee-Aware Calculations**: All decisions include exchange fee considerations
- **Execution Verification**: Strict confirmation of actual trade execution
- **Position Monitoring**: Continuous oversight with 1-minute intervals
- **Smart Completion Detection**: Distinguishes between intentions and actual executions

### 🛡️ **Professional Risk Management**
- **Profit Protection**: Automatic stop-loss tightening as profits increase
- **Break-even Management**: Fee-adjusted break-even calculations
- **Context Length Handling**: Automatic prompt optimization for API limits
- **Error Recovery**: Comprehensive error analysis and retry mechanisms
- **Cost Tracking**: Real-time API usage and cost monitoring

### 🌐 **Multi-Session Architecture**
- **Independent Sessions**: Run multiple strategies simultaneously
- **Session Isolation**: Separate databases, state files, and dashboards
- **Flexible Configuration**: Per-session coins, styles, and intervals
- **Scalable Design**: Support for unlimited concurrent trading sessions

## 🚀 Quick Start

### 1. **Installation**
```bash
pip install -e .
```

### 2. **Ultra-Aggressive Configuration**
```bash
# Set up for 20% daily returns with high leverage
claude-trader config --style aggressive --coins BTC,ETH,SOL --interval 1
```

### 3. **Start 24/7 Trading**
```bash
# Single session
claude-trader start

# Multiple independent sessions
claude-trader start --session btc-scalping --coins BTC --interval 1
claude-trader start --session eth-swing --coins ETH --interval 5
claude-trader start --session trending --coins AUTO --interval 2
```

## 📊 Advanced Commands

### **Configuration Management**
```bash
# View current configuration
claude-trader config --show

# Ultra-aggressive setup
claude-trader config --style aggressive --coins BTC,ETH,SOL --interval 1

# Dynamic trending coins
claude-trader config --coins AUTO

# Custom monitoring frequency
claude-trader config --interval 1  # 1-minute monitoring
```

### **Session Management**
```bash
# Independent sessions with different strategies
claude-trader start --session btc-only --coins BTC --style aggressive --interval 1
claude-trader start --session trending --coins AUTO --style aggressive --interval 2
claude-trader start --session multi-coin --coins BTC,ETH,SOL --interval 5

# Manual trade control
claude-trader skip --reason "Market conditions changed"
claude-trader force-next  # Force new trade immediately
```

### **Monitoring and Analysis**
```bash
# Real-time status
claude-trader status

# Trade history analysis
claude-trader history --limit 20

# Web dashboard with real-time updates
claude-trader dashboard --port 5000
```

### **Testing and Simulation**
```bash
# Test Claude CLI integration
claude-trader test

# Simulate trading cycles
claude-trader simulate --cycles 5
```

## 🎯 Trading Styles

### **Aggressive (Recommended for 20% Target)**
- **Description**: Systematic quantitative trader using data-driven analysis for high-return strategies
- **Risk Tolerance**: Very high
- **Position Preference**: Larger positions based on statistical analysis and risk assessment
- **Daily Target**: 20% daily returns through analytical trading
- **Leverage Usage**: Appropriate leverage based on market volatility and risk assessment

### **Moderate**
- **Description**: Balanced trader seeking good profits while managing risk appropriately
- **Risk Tolerance**: Medium
- **Position Preference**: Moderate positions balancing risk and reward

### **Cautious**
- **Description**: Careful trader prioritizing capital preservation while seeking steady profits
- **Risk Tolerance**: Low
- **Position Preference**: Smaller positions with tight risk management

### **Conservative**
- **Description**: Very conservative trader focusing on capital protection with minimal risk
- **Risk Tolerance**: Very low
- **Position Preference**: Small positions with strict stop losses

## 🌐 Advanced Web Dashboard

### **Real-Time Trading Intelligence**
- **📊 Live Statistics**: Total trades, success rate, average returns, cost analysis
- **📈 Trade Timeline**: Complete trade lifecycle with Claude decision reasoning
- **💰 Cost Tracking**: API usage costs, average cost per interaction, ROI analysis
- **🎯 Performance Metrics**: Daily return progress, leverage usage, risk metrics
- **📱 Responsive Design**: Full mobile and desktop compatibility

### **Dashboard Features**
- **Auto-refresh**: Real-time updates every 30 seconds
- **Trade Details**: Full Claude responses and reasoning for each decision
- **Session Management**: Multi-session support with separate dashboards
- **Cost Analysis**: Detailed API cost breakdown and profitability analysis
- **Risk Monitoring**: Real-time risk exposure and position analysis

**Access**: `http://localhost:5000` (or session-specific ports)

## 🔧 Advanced Configuration

### **Ultra-Aggressive Setup (claude_trader.yaml)**
```yaml
trading:
  style: aggressive
  coins: ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE']  # Or ['AUTO'] for trending
  position_size: {min: 5, max: 25}
  monitoring_interval: 1  # 1-minute monitoring

styles:
  aggressive:
    description: "systematic quantitative trader using data-driven analysis for high-return strategies"
    risk_tolerance: "very high"
    position_preference: "larger positions based on statistical analysis and risk assessment"
    daily_target: "20% daily returns through analytical trading"
    leverage_usage: "appropriate leverage based on market volatility and risk assessment"

advanced:
  completion_keywords:
    - "trade completed"
    - "position closed"
    - "order executed"
    - "successfully closed"
    - "execution confirmed"
```

## 🎯 How It Works

### **1. Trade Initiation**
- **Market Analysis**: Comprehensive futures market analysis using advanced MCP tools
- **Coin Selection**: Dynamic trending coin identification or specific coin focus
- **Position Sizing**: High-leverage position calculation for 20% daily target
- **Risk Management**: POC and Value Area analysis for precise entry points

### **2. Continuous Monitoring**
- **Real-time Updates**: 1-minute monitoring intervals for rapid market response
- **TP/SL Management**: Dynamic profit protection and loss minimization
- **Fee Calculations**: All decisions include maker/taker fee considerations
- **Position Isolation**: Only monitors positions created by this session

### **3. Intelligent Completion**
- **Execution Verification**: Requires actual trade execution confirmation
- **Smart Detection**: Distinguishes between intentions and actual executions
- **Automatic Cycling**: Seamless transition from completed trade to new trade initiation

## 💰 Cost Tracking & ROI

### **Real-Time Cost Analysis**
- **Per-Interaction Costs**: ~$0.008 per Claude API call
- **Daily Cost Estimates**: ~$11.52 for 1-minute monitoring (1,440 calls/day)
- **ROI Calculation**: 2,150x cost recovery on successful 20% daily returns
- **Cost Optimization**: Automatic prompt shortening for context length management

### **Example Cost Breakdown**
```
Trade Lifecycle Costs:
- Initiation: $0.0088
- Monitoring (10 cycles): $0.0750  
- Completion: $0.0092
Total Trade Cost: $0.0930

ROI on $1000 position with 20% return:
- Trade Cost: $0.093
- Profit: $200
- ROI: 2,150x cost recovery
```

## 🛡️ Safety & Risk Management

### **⚠️ High-Risk Trading System**
This system uses `--dangerously-skip-permissions` for uninterrupted operation:

- **Risk**: Claude can execute trades without permission prompts
- **Benefit**: Uninterrupted 24/7 trading execution
- **Recommendation**: Use in secure, isolated environment
- **Capital Risk**: Only use funds you can afford to lose entirely

### **Risk Mitigation**
- **Position Isolation**: Only manages positions it creates
- **Session Separation**: Independent operation across multiple sessions  
- **Execution Verification**: Confirms actual trade execution before completion
- **Cost Monitoring**: Real-time API cost tracking and limits
- **Error Recovery**: Comprehensive error handling and retry mechanisms

## 🔧 Environment Setup

### **Required Environment Variables**
```bash
export ANTHROPIC_MODEL='us.anthropic.claude-sonnet-4-20250514-v1:0'
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_PROFILE=fintech-tax-bedrock-full-access-profile
export AWS_REGION=us-west-2
```

### **MCP Server Requirements**
- **Bybit MCP Server**: Core trading functionality
- **Advanced MCP Tools**: Volume profile, correlation analysis, trending coins
- **News MCP Server**: Market sentiment analysis (optional)

## 📋 Requirements

- **Python 3.9+**
- **Claude CLI** command available in PATH
- **Bybit MCP Server** configured and running
- **AWS Bedrock** access with appropriate permissions
- **Advanced MCP Tools** for enhanced analysis

## 🎯 Perfect For

- **Aggressive Traders**: Seeking 20% daily returns with high leverage
- **Systematic Trading**: Data-driven, emotion-free trading decisions
- **24/7 Operations**: Continuous market monitoring and execution
- **Multi-Strategy**: Running multiple independent trading sessions
- **Professional Trading**: Institutional-grade analysis and risk management

## 📈 Success Metrics

- **Daily Return Target**: 20% on total wallet value
- **Leverage Utilization**: 10x-100x based on market conditions
- **Monitoring Frequency**: 1-minute intervals for maximum responsiveness
- **Cost Efficiency**: ~$0.008 per trading decision
- **Position Accuracy**: Only manages self-created positions

## 🚀 Get Started Now

```bash
# Install the system
pip install -e .

# Configure for ultra-aggressive trading
claude-trader config --style aggressive --coins AUTO --interval 1

# Start your first 20% daily return session
claude-trader start --session main-trading

# Monitor via web dashboard
claude-trader dashboard
```

**Ready to achieve 20% daily returns through systematic, AI-powered futures trading!** 🎯

## 📄 License

MIT License - Trade at your own risk. This system is designed for experienced traders who understand the risks of high-leverage futures trading.
