"""
Main Trading Application - Crypto Trading Bot using Claude Code and Bybit MCP
"""
import asyncio
import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import subprocess
import tempfile
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Track trading performance and statistics"""
    
    def __init__(self):
        self.trades = []
        self.total_pnl = 0.0
        self.start_time = datetime.now()
        
    def record_trade(self, trade_result: Dict):
        """Record a completed trade"""
        self.trades.append({
            **trade_result,
            'timestamp': datetime.now().isoformat()
        })
        
        pnl = trade_result.get('pnl', 0)
        self.total_pnl += pnl
        
        logger.info(f"Trade recorded: {trade_result.get('symbol')} PnL: ${pnl:.2f}")
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl_per_trade': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        winning_trades = [t for t in self.trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in self.trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(self.trades) * 100
        avg_pnl = self.total_pnl / len(self.trades)
        
        pnls = [t.get('pnl', 0) for t in self.trades]
        best_trade = max(pnls) if pnls else 0
        worst_trade = min(pnls) if pnls else 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(self.total_pnl, 2),
            'avg_pnl_per_trade': round(avg_pnl, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'trading_days': (datetime.now() - self.start_time).days + 1
        }

class TradingBot:
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the trading bot"""
        self.config = self.load_config(config_path)
        self.current_position = None
        self.current_symbol = None
        self.trading_active = True
        self.paper_trading = self.config.get('trading', {}).get('paper_trading', True)
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.last_trade_time = None
        self.performance_tracker = PerformanceTracker()
        
        # Load API credentials
        self._load_api_credentials()
        
        logger.info(f"Trading bot initialized - Paper Trading: {self.paper_trading}")
    
    def _load_api_credentials(self):
        """Load API credentials from environment variables"""
        import os
        
        bybit_config = self.config.get('bybit', {})
        api_config = bybit_config.get('api_credentials', {})
        
        if api_config.get('use_environment_variables', True):
            api_key_env = api_config.get('api_key_env', 'BYBIT_API_KEY')
            secret_key_env = api_config.get('secret_key_env', 'BYBIT_SECRET_KEY')
            
            self.api_key = os.getenv(api_key_env)
            self.secret_key = os.getenv(secret_key_env)
            
            if not self.api_key or not self.secret_key:
                logger.warning("API credentials not found in environment variables")
                if not self.paper_trading:
                    logger.error("Real trading requires API credentials!")
                    raise ValueError("API credentials required for real trading")
            else:
                logger.info("API credentials loaded successfully")
        else:
            logger.warning("API credentials not configured")
    
    def is_trading_hours(self) -> bool:
        """Check if within allowed trading hours"""
        trading_hours = self.config.get('trading', {}).get('trading_hours', {})
        
        if not trading_hours.get('enabled', True):
            return True
        
        from datetime import datetime, time
        import pytz
        
        timezone = trading_hours.get('timezone', 'UTC')
        tz = pytz.timezone(timezone)
        now = datetime.now(tz).time()
        
        start_hour = trading_hours.get('start_hour', 0)
        end_hour = trading_hours.get('end_hour', 23)
        
        start_time = time(start_hour, 0)
        end_time = time(end_hour, 0)
        
        return start_time <= now <= end_time
    
    def check_safety_limits(self) -> bool:
        """Check if trading is allowed based on safety limits"""
        safety_config = self.config.get('safety', {})
        monitoring_config = self.config.get('monitoring', {})
        
        # Check emergency stop
        if safety_config.get('emergency_stop', False):
            logger.warning("Emergency stop is active - trading disabled")
            return False
        
        # Check daily trade limit
        max_daily_trades = monitoring_config.get('max_daily_trades', 100)
        if self.daily_trades >= max_daily_trades:
            logger.warning(f"Daily trade limit reached: {self.daily_trades}/{max_daily_trades}")
            return False
        
        # Check daily loss limit
        max_daily_loss = monitoring_config.get('max_daily_loss_usd', 1000)
        if self.daily_loss >= max_daily_loss:
            logger.warning(f"Daily loss limit reached: ${self.daily_loss:.2f}/${max_daily_loss}")
            return False
        
        # Check cooldown after loss
        if self.last_trade_time:
            cooldown_minutes = safety_config.get('cooldown_after_loss_minutes', 0)
            if cooldown_minutes > 0:
                time_since_last_trade = (datetime.now() - self.last_trade_time).total_seconds() / 60
                if time_since_last_trade < cooldown_minutes:
                    logger.info(f"Cooldown active: {cooldown_minutes - time_since_last_trade:.1f} minutes remaining")
                    return False
        
        return True
    
    def validate_position_size(self, size: float, symbol: str, current_price: float) -> float:
        """Validate and limit position size"""
        safety_config = self.config.get('safety', {})
        position_limits = safety_config.get('position_size_limits', {})
        
        # Calculate position value in USD
        position_value = size * current_price
        
        # Check minimum position size
        min_usd = position_limits.get('min_usd', 10)
        if position_value < min_usd:
            logger.warning(f"Position size too small: ${position_value:.2f} < ${min_usd}")
            return 0
        
        # Check maximum position size
        max_usd = position_limits.get('max_usd', 100)
        if position_value > max_usd:
            adjusted_size = max_usd / current_price
            logger.warning(f"Position size limited: ${position_value:.2f} -> ${max_usd}")
            return adjusted_size
        
        return size
    
    async def send_notification(self, message: str, level: str = "INFO"):
        """Send trading notifications"""
        logger.log(getattr(logging, level), f"NOTIFICATION: {message}")
        
        # Here you could add email, Discord, Slack notifications
        # For now, just log the notification
        
    def load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    async def get_trending_coins(self) -> List[str]:
        """Get trending coins from Bybit MCP"""
        try:
            # Use MCP tool to get trending coins
            result = await self.use_mcp_tool(
                "bybit",
                "get_trending_coins",
                {
                    "category": "spot",
                    "sortBy": "price_change_24h",
                    "direction": "upward",
                    "limit": 20,
                    "minVolume": 1000000,  # Minimum volume filter
                    "minPriceChange": 5    # Minimum 5% price change
                }
            )
            
            if result and 'trending' in result:
                symbols = [coin['symbol'] for coin in result['trending']]
                logger.info(f"Found {len(symbols)} trending coins: {symbols[:5]}...")
                return symbols
            else:
                # Fallback to config coins
                return self.config['trading']['coins']
                
        except Exception as e:
            logger.error(f"Error getting trending coins: {e}")
            return self.config['trading']['coins']
    
    async def use_mcp_tool(self, server_name: str, tool_name: str, arguments: Dict) -> Dict:
        """Use MCP tools via the MCP client"""
        from mcp_client import use_mcp_tool
        return await use_mcp_tool(server_name, tool_name, arguments)
    
    async def analyze_coin_with_claude_code(self, symbol: str) -> Dict:
        """Analyze a coin using Claude Code with MCP data"""
        try:
            logger.info(f"Analyzing {symbol} with Claude Code")
            
            # Create Claude Code script that uses MCP tools
            script = self.create_analysis_script(symbol)
            
            # Execute script with Claude Code
            result = await self.execute_claude_code(script)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {'action': 'HOLD', 'reason': f'Analysis error: {str(e)}'}
    
    def create_analysis_script(self, symbol: str) -> str:
        """Create Python script for Claude Code execution"""
        script = f'''
import json
import asyncio
from datetime import datetime

# This script will be executed in Claude Code environment
# It will use the MCP tools to analyze {symbol}

async def analyze_trading_opportunity():
    """Main analysis function using MCP tools"""
    try:
        symbol = "{symbol}"
        
        # Step 1: Get multi-timeframe momentum analysis
        momentum_result = await use_mcp_tool("bybit", "scan_multi_timeframe_momentum", {{
            "category": "spot",
            "symbol": symbol,
            "timeframes": ["15", "60", "240", "D"],
            "limit": 50
        }})
        
        # Step 2: Get RSI analysis
        rsi_result = await use_mcp_tool("bybit", "calculate_rsi", {{
            "category": "spot",
            "symbol": symbol,
            "interval": "60",
            "period": 14,
            "limit": 100
        }})
        
        # Step 3: Get MACD analysis
        macd_result = await use_mcp_tool("bybit", "calculate_macd", {{
            "category": "spot",
            "symbol": symbol,
            "interval": "60",
            "fastPeriod": 12,
            "slowPeriod": 26,
            "signalPeriod": 9,
            "limit": 100
        }})
        
        # Step 4: Get Bollinger Bands
        bb_result = await use_mcp_tool("bybit", "calculate_bollinger_bands", {{
            "category": "spot",
            "symbol": symbol,
            "interval": "60",
            "period": 20,
            "stdDev": 2,
            "limit": 100
        }})
        
        # Step 5: Get current price
        ticker_result = await use_mcp_tool("bybit", "get_tickers", {{
            "category": "spot",
            "symbol": symbol
        }})
        
        # Analyze all the data
        analysis = analyze_signals(momentum_result, rsi_result, macd_result, bb_result, ticker_result)
        
        return analysis
        
    except Exception as e:
        return {{
            'action': 'HOLD',
            'symbol': symbol,
            'reason': f'Analysis error: {{str(e)}}',
            'error': True,
            'timestamp': datetime.now().isoformat()
        }}

def analyze_signals(momentum, rsi, macd, bb, ticker):
    """Analyze all signals and make trading decision"""
    signals = []
    confidence = 0
    
    # Extract current price
    current_price = 0
    if ticker and 'result' in ticker and 'list' in ticker['result']:
        current_price = float(ticker['result']['list'][0]['lastPrice'])
    
    # Multi-timeframe momentum analysis
    if momentum and 'overallMomentum' in momentum:
        overall_momentum = momentum['overallMomentum']
        confluence = momentum.get('confluenceAnalysis', {{}})
        
        if overall_momentum == 'bullish' and confluence.get('bullishTimeframes', 0) >= 3:
            signals.append(('BUY', 'Strong multi-timeframe bullish momentum'))
            confidence += 0.3
        elif overall_momentum == 'bearish' and confluence.get('bearishTimeframes', 0) >= 3:
            signals.append(('SELL', 'Strong multi-timeframe bearish momentum'))
            confidence += 0.3
    
    # RSI analysis
    if rsi and 'rsi' in rsi:
        rsi_value = rsi['rsi']
        rsi_signal = rsi.get('signal', '')
        
        if rsi_signal == 'oversold' and rsi_value < 30:
            signals.append(('BUY', f'RSI oversold at {{rsi_value:.2f}}'))
            confidence += 0.25
        elif rsi_signal == 'overbought' and rsi_value > 70:
            signals.append(('SELL', f'RSI overbought at {{rsi_value:.2f}}'))
            confidence += 0.25
    
    # MACD analysis
    if macd and 'signals' in macd:
        macd_signals = macd['signals']
        if 'bullish_crossover' in macd_signals:
            signals.append(('BUY', 'MACD bullish crossover'))
            confidence += 0.2
        elif 'bearish_crossover' in macd_signals:
            signals.append(('SELL', 'MACD bearish crossover'))
            confidence += 0.2
    
    # Bollinger Bands analysis
    if bb and 'signals' in bb:
        bb_signals = bb['signals']
        if 'oversold_bounce' in bb_signals:
            signals.append(('BUY', 'Bollinger Bands oversold bounce'))
            confidence += 0.15
        elif 'overbought_rejection' in bb_signals:
            signals.append(('SELL', 'Bollinger Bands overbought rejection'))
            confidence += 0.15
    
    # Decision making
    buy_signals = [s for s in signals if s[0] == 'BUY']
    sell_signals = [s for s in signals if s[0] == 'SELL']
    
    if len(buy_signals) >= 2 and confidence >= 0.4:
        # Calculate position sizing and risk management
        stop_loss_pct = 0.02  # 2% stop loss
        take_profit_pct = 0.04  # 4% take profit (2:1 risk reward)
        
        return {{
            'action': 'BUY',
            'symbol': '{symbol}',
            'entry_price': current_price,
            'stop_loss': current_price * (1 - stop_loss_pct),
            'take_profit': current_price * (1 + take_profit_pct),
            'confidence': min(confidence, 1.0),
            'reasons': [s[1] for s in buy_signals],
            'all_signals': signals,
            'timestamp': datetime.now().isoformat()
        }}
    elif len(sell_signals) >= 2 and confidence >= 0.4:
        return {{
            'action': 'SELL',
            'symbol': '{symbol}',
            'entry_price': current_price,
            'confidence': min(confidence, 1.0),
            'reasons': [s[1] for s in sell_signals],
            'all_signals': signals,
            'timestamp': datetime.now().isoformat()
        }}
    else:
        return {{
            'action': 'HOLD',
            'symbol': '{symbol}',
            'current_price': current_price,
            'confidence': confidence,
            'reasons': ['Insufficient signals for entry'],
            'all_signals': signals,
            'timestamp': datetime.now().isoformat()
        }}

# Mock MCP tool function for Claude Code environment
async def use_mcp_tool(server_name, tool_name, arguments):
    """Mock function - in real Claude Code, this would use actual MCP"""
    # This would be replaced with actual MCP calls in Claude Code
    return {{"mock": True, "tool": tool_name}}

# Execute analysis
if __name__ == "__main__":
    result = asyncio.run(analyze_trading_opportunity())
    print(json.dumps(result, indent=2))
'''
        return script
    
    async def execute_claude_code(self, script: str) -> Dict:
        """Execute Python script using Claude Code CLI"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script)
                script_path = f.name
            
            try:
                # Execute with claude-code CLI
                cmd = ['claude-code', 'run', script_path]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=300
                )
                
                if process.returncode == 0:
                    output = stdout.decode('utf-8').strip()
                    try:
                        return json.loads(output)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Claude Code output: {output}")
                        return {'action': 'HOLD', 'reason': 'Failed to parse analysis'}
                else:
                    error_msg = stderr.decode('utf-8')
                    logger.error(f"Claude Code execution failed: {error_msg}")
                    return {'action': 'HOLD', 'reason': f'Execution failed: {error_msg}'}
            
            finally:
                # Clean up
                try:
                    os.unlink(script_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error executing Claude Code: {e}")
            return {'action': 'HOLD', 'reason': f'Execution error: {str(e)}'}
    
    async def execute_trade(self, analysis: Dict) -> bool:
        """Execute trade based on analysis"""
        try:
            if analysis['action'] not in ['BUY', 'SELL']:
                return False
            
            symbol = analysis['symbol']
            action = analysis['action']
            entry_price = analysis.get('entry_price', 0)
            
            logger.info(f"Executing {action} trade for {symbol} at {entry_price}")
            
            # Get wallet balance
            balance_result = await self.use_mcp_tool("bybit", "get_wallet_balance", {
                "accountType": "UNIFIED"
            })
            
            # Calculate position size (risk 2% of account)
            # This would use the MCP position sizing tools
            position_size_result = await self.use_mcp_tool("bybit", "calculate_position_size", {
                "category": "spot",
                "symbol": symbol,
                "accountBalance": 10000,  # This would come from balance_result
                "riskPercentage": 2,
                "stopLossPrice": analysis.get('stop_loss', entry_price * 0.98),
                "currentPrice": entry_price
            })
            
            # Place order using MCP
            order_result = await self.use_mcp_tool("bybit", "place_order", {
                "category": "spot",
                "symbol": symbol,
                "side": "Buy" if action == "BUY" else "Sell",
                "orderType": "Market",
                "qty": "0.001",  # This would come from position_size_result
                "takeProfit": str(analysis.get('take_profit', 0)),
                "stopLoss": str(analysis.get('stop_loss', 0))
            })
            
            if order_result:
                self.current_position = {
                    'symbol': symbol,
                    'side': action,
                    'entry_price': entry_price,
                    'stop_loss': analysis.get('stop_loss'),
                    'take_profit': analysis.get('take_profit'),
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Trade executed successfully: {action} {symbol}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    async def monitor_position(self) -> bool:
        """Monitor current position and adjust TP/SL"""
        if not self.current_position:
            return True
        
        try:
            symbol = self.current_position['symbol']
            
            # Get current position data
            positions_result = await self.use_mcp_tool("bybit", "get_positions", {
                "category": "spot",
                "symbol": symbol
            })
            
            # Get current market data for monitoring
            ticker_result = await self.use_mcp_tool("bybit", "get_tickers", {
                "category": "spot",
                "symbol": symbol
            })
            
            # Use Claude Code to analyze position and get adjustment suggestions
            monitoring_script = self.create_monitoring_script(symbol, self.current_position, ticker_result)
            monitoring_result = await self.execute_claude_code(monitoring_script)
            
            # Process monitoring suggestions
            if monitoring_result and 'suggestions' in monitoring_result:
                for suggestion in monitoring_result['suggestions']:
                    if suggestion['action'] == 'ADJUST_SL':
                        # Adjust stop loss
                        await self.use_mcp_tool("bybit", "set_trading_stop", {
                            "category": "spot",
                            "symbol": symbol,
                            "stopLoss": str(suggestion['new_stop_loss'])
                        })
                        logger.info(f"Adjusted stop loss for {symbol}: {suggestion['new_stop_loss']}")
                    
                    elif suggestion['action'] == 'ADJUST_TP':
                        # Adjust take profit
                        await self.use_mcp_tool("bybit", "set_trading_stop", {
                            "category": "spot",
                            "symbol": symbol,
                            "takeProfit": str(suggestion['new_take_profit'])
                        })
                        logger.info(f"Adjusted take profit for {symbol}: {suggestion['new_take_profit']}")
                    
                    elif suggestion['action'] == 'EXIT':
                        # Close position
                        await self.close_position()
                        return False  # Position closed
            
            return True  # Continue monitoring
            
        except Exception as e:
            logger.error(f"Error monitoring position: {e}")
            return True
    
    def create_monitoring_script(self, symbol: str, position: Dict, market_data: Dict) -> str:
        """Create monitoring script for Claude Code"""
        script = f'''
import json
from datetime import datetime

# Position monitoring for {symbol}
position_data = {json.dumps(position, indent=2)}
market_data = {json.dumps(market_data, indent=2)}

def monitor_position():
    """Monitor position and suggest adjustments"""
    try:
        current_price = 0
        if market_data and 'result' in market_data and 'list' in market_data['result']:
            current_price = float(market_data['result']['list'][0]['lastPrice'])
        
        entry_price = position_data.get('entry_price', current_price)
        side = position_data.get('side', 'BUY')
        
        # Calculate profit percentage
        if side == 'BUY':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        suggestions = []
        
        # Trailing stop logic
        if profit_pct > 2:  # Move to breakeven if 2% profit
            if side == 'BUY':
                new_stop_loss = entry_price * 1.001  # Small buffer above entry
            else:
                new_stop_loss = entry_price * 0.999
            
            suggestions.append({{
                'action': 'ADJUST_SL',
                'new_stop_loss': new_stop_loss,
                'reason': 'Moving stop loss to breakeven'
            }})
        
        # Take profit extension
        if profit_pct > 5:  # If 5% profit, extend TP
            if side == 'BUY':
                new_take_profit = current_price * 1.03  # 3% above current
            else:
                new_take_profit = current_price * 0.97
            
            suggestions.append({{
                'action': 'ADJUST_TP',
                'new_take_profit': new_take_profit,
                'reason': 'Extending take profit target'
            }})
        
        # Exit conditions
        if profit_pct < -5:  # 5% loss
            suggestions.append({{
                'action': 'EXIT',
                'reason': 'Stop loss threshold reached'
            }})
        elif profit_pct > 10:  # 10% profit
            suggestions.append({{
                'action': 'EXIT',
                'reason': 'Take profit threshold reached'
            }})
        
        return {{
            'symbol': '{symbol}',
            'current_price': current_price,
            'profit_pct': profit_pct,
            'suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }}
    
    except Exception as e:
        return {{
            'error': True,
            'reason': f'Monitoring error: {{str(e)}}'
        }}

result = monitor_position()
print(json.dumps(result, indent=2))
'''
        return script
    
    async def close_position(self):
        """Close current position"""
        if not self.current_position:
            return
        
        try:
            symbol = self.current_position['symbol']
            
            # Cancel any open orders first
            await self.use_mcp_tool("bybit", "cancel_order", {
                "category": "spot",
                "symbol": symbol
            })
            
            # Close position (for spot, this would be selling the asset)
            logger.info(f"Closing position for {symbol}")
            
            self.current_position = None
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def run_trading_cycle(self):
        """Run one complete trading cycle with safety checks"""
        try:
            # Safety checks before trading
            if not self.is_trading_hours():
                logger.info("Outside trading hours - skipping cycle")
                return
            
            if not self.check_safety_limits():
                logger.info("Safety limits exceeded - skipping cycle")
                return
            
            # Step 1: Get trending coins
            trending_coins = await self.get_trending_coins()
            
            # Step 2: Select a coin (random selection from trending)
            if not trending_coins:
                logger.warning("No trending coins found, using config coins")
                trending_coins = self.config['trading']['coins']
            
            selected_coin = random.choice(trending_coins)
            logger.info(f"Selected coin for analysis: {selected_coin}")
            
            # Step 3: Analyze with Claude Code
            analysis = await self.analyze_coin_with_claude_code(selected_coin)
            
            # Check confidence threshold
            min_confidence = self.config.get('trading', {}).get('min_confidence_threshold', 0.6)
            
            # Step 4: Execute trade if signal is strong
            if (analysis['action'] in ['BUY', 'SELL'] and 
                analysis.get('confidence', 0) >= min_confidence):
                
                await self.send_notification(
                    f"Strong signal detected: {analysis['action']} {selected_coin} "
                    f"(Confidence: {analysis.get('confidence', 0):.2f})"
                )
                
                trade_executed = await self.execute_trade(analysis)
                
                if trade_executed:
                    self.daily_trades += 1
                    self.last_trade_time = datetime.now()
                    
                    # Step 5: Monitor position until closed
                    while self.current_position and self.trading_active:
                        continue_monitoring = await self.monitor_position()
                        if not continue_monitoring:
                            break
                        await asyncio.sleep(60)  # Check every minute
                    
                    # Record trade completion
                    if not self.current_position:  # Position was closed
                        # Calculate simulated PnL for paper trading
                        pnl = self._calculate_simulated_pnl(analysis)
                        
                        self.performance_tracker.record_trade({
                            'symbol': selected_coin,
                            'action': analysis['action'],
                            'entry_price': analysis.get('entry_price', 0),
                            'pnl': pnl,
                            'confidence': analysis.get('confidence', 0)
                        })
                        
                        if pnl < 0:
                            self.daily_loss += abs(pnl)
                        
                        await self.send_notification(
                            f"Trade completed: {selected_coin} PnL: ${pnl:.2f}"
                        )
            else:
                confidence = analysis.get('confidence', 0)
                logger.info(f"Signal too weak for {selected_coin}: "
                          f"Action={analysis['action']}, Confidence={confidence:.2f} "
                          f"(Required: {min_confidence:.2f})")
                logger.info(f"Reasons: {analysis.get('reasons', [])}")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")
            await self.send_notification(f"Trading cycle error: {str(e)}", "ERROR")
    
    def _calculate_simulated_pnl(self, analysis: Dict) -> float:
        """Calculate simulated PnL for paper trading"""
        import random
        
        # Simulate realistic PnL based on confidence and market conditions
        confidence = analysis.get('confidence', 0.5)
        
        # Higher confidence generally leads to better results, but not always
        base_return = (confidence - 0.5) * 0.1  # -5% to +5% base return
        
        # Add some randomness to simulate market volatility
        volatility = random.uniform(-0.05, 0.05)  # ±5% volatility
        
        # Calculate final return percentage
        return_pct = base_return + volatility
        
        # Apply to position size (simulate $50 position)
        position_value = 50.0
        pnl = position_value * return_pct
        
        return round(pnl, 2)
    
    async def run(self):
        """Main trading loop"""
        logger.info("Starting Crypto Trading Bot")
        
        while self.trading_active:
            try:
                # Run one trading cycle
                await self.run_trading_cycle()
                
                # Wait before next cycle (only if no position)
                if not self.current_position:
                    logger.info("Waiting 5 minutes before next analysis...")
                    await asyncio.sleep(300)  # 5 minutes
                
            except KeyboardInterrupt:
                logger.info("Shutting down trading bot...")
                self.trading_active = False
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry

async def main():
    """Main entry point"""
    bot = TradingBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
