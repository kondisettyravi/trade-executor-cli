"""
Claude Code Interface - Handles Claude Code API calls and session management
"""
import asyncio
import json
import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ClaudeCodeInterface:
    def __init__(self, config: Dict):
        """
        Initialize Claude Code interface
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.claude_config = config.get('claude_code', {})
        self.max_retries = self.claude_config.get('max_retries', 3)
        self.timeout = self.claude_config.get('timeout', 300)
        self.session_timeout = self.claude_config.get('session_timeout', 1800)
        
    async def create_trading_analysis_script(self, symbol: str, market_data: Dict) -> str:
        """
        Create a Python script for trading analysis that will be executed in Claude Code
        
        Args:
            symbol: Trading symbol
            market_data: Market data including klines, ticker, orderbook
            
        Returns:
            Python script as string
        """
        script = f'''
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Market data for {symbol}
market_data = {json.dumps(market_data, indent=2)}

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gains = pd.Series(gains).rolling(window=period).mean()
    avg_losses = pd.Series(losses).rolling(window=period).mean()
    
    rs = avg_gains / avg_losses
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD indicator"""
    prices_series = pd.Series(prices)
    ema_fast = prices_series.ewm(span=fast).mean()
    ema_slow = prices_series.ewm(span=slow).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return {{
        'macd': macd_line.iloc[-1],
        'signal': signal_line.iloc[-1],
        'histogram': histogram.iloc[-1]
    }}

def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range"""
    high_low = np.array(highs) - np.array(lows)
    high_close = np.abs(np.array(highs) - np.roll(closes, 1))
    low_close = np.abs(np.array(lows) - np.roll(closes, 1))
    
    true_ranges = np.maximum(high_low, np.maximum(high_close, low_close))
    atr = pd.Series(true_ranges).rolling(window=period).mean()
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0

def analyze_volume_momentum(volumes, prices, period=20):
    """Analyze volume and price momentum"""
    volumes = np.array(volumes)
    prices = np.array(prices)
    
    avg_volume = np.mean(volumes[-period:])
    current_volume = volumes[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
    
    price_change = (prices[-1] - prices[-period]) / prices[-period] * 100
    
    return {{
        'volume_ratio': volume_ratio,
        'price_momentum': price_change,
        'avg_volume': avg_volume
    }}

def analyze_market_structure(highs, lows, closes):
    """Analyze market structure for trend direction"""
    recent_highs = highs[-10:]
    recent_lows = lows[-10:]
    recent_closes = closes[-10:]
    
    # Check for higher highs and higher lows (uptrend)
    higher_highs = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] > recent_highs[i-1])
    higher_lows = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] > recent_lows[i-1])
    
    # Check for lower highs and lower lows (downtrend)
    lower_highs = sum(1 for i in range(1, len(recent_highs)) if recent_highs[i] < recent_highs[i-1])
    lower_lows = sum(1 for i in range(1, len(recent_lows)) if recent_lows[i] < recent_lows[i-1])
    
    if higher_highs >= 6 and higher_lows >= 6:
        return "UPTREND"
    elif lower_highs >= 6 and lower_lows >= 6:
        return "DOWNTREND"
    else:
        return "SIDEWAYS"

def make_trading_decision():
    """Main trading analysis function"""
    try:
        # Extract kline data
        klines = market_data.get('kline_data', {{}}).get('result', {{}}).get('list', [])
        if not klines:
            return {{'action': 'HOLD', 'reason': 'No kline data available'}}
        
        # Parse kline data (format: [timestamp, open, high, low, close, volume, turnover])
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        
        if len(closes) < 50:
            return {{'action': 'HOLD', 'reason': 'Insufficient data for analysis'}}
        
        current_price = closes[-1]
        
        # Technical indicators
        rsi = calculate_rsi(closes)
        macd_data = calculate_macd(closes)
        atr = calculate_atr(highs, lows, closes)
        volume_data = analyze_volume_momentum(volumes, closes)
        trend = analyze_market_structure(highs, lows, closes)
        
        # Trading logic
        signals = []
        
        # RSI signals
        if rsi < 30:
            signals.append(('BUY', 'RSI oversold'))
        elif rsi > 70:
            signals.append(('SELL', 'RSI overbought'))
        
        # MACD signals
        if macd_data['macd'] > macd_data['signal'] and macd_data['histogram'] > 0:
            signals.append(('BUY', 'MACD bullish crossover'))
        elif macd_data['macd'] < macd_data['signal'] and macd_data['histogram'] < 0:
            signals.append(('SELL', 'MACD bearish crossover'))
        
        # Volume momentum
        if volume_data['volume_ratio'] > 1.5 and volume_data['price_momentum'] > 2:
            signals.append(('BUY', 'Strong volume with positive momentum'))
        elif volume_data['volume_ratio'] > 1.5 and volume_data['price_momentum'] < -2:
            signals.append(('SELL', 'Strong volume with negative momentum'))
        
        # Trend confirmation
        if trend == "UPTREND" and any(s[0] == 'BUY' for s in signals):
            signals.append(('BUY', 'Trend confirmation'))
        elif trend == "DOWNTREND" and any(s[0] == 'SELL' for s in signals):
            signals.append(('SELL', 'Trend confirmation'))
        
        # Decision making
        buy_signals = [s for s in signals if s[0] == 'BUY']
        sell_signals = [s for s in signals if s[0] == 'SELL']
        
        if len(buy_signals) >= 2:
            # Calculate stop loss and take profit
            stop_loss = current_price - (atr * 2)
            take_profit = current_price + (atr * 4)  # 2:1 risk reward
            
            return {{
                'action': 'BUY',
                'symbol': '{symbol}',
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': min(len(buy_signals) * 0.3, 1.0),
                'reasons': [s[1] for s in buy_signals],
                'technical_data': {{
                    'rsi': rsi,
                    'macd': macd_data,
                    'atr': atr,
                    'volume_ratio': volume_data['volume_ratio'],
                    'trend': trend
                }}
            }}
        elif len(sell_signals) >= 2:
            # For spot trading, we typically don't short, so this would be a sell signal for existing positions
            return {{
                'action': 'SELL',
                'symbol': '{symbol}',
                'entry_price': current_price,
                'confidence': min(len(sell_signals) * 0.3, 1.0),
                'reasons': [s[1] for s in sell_signals],
                'technical_data': {{
                    'rsi': rsi,
                    'macd': macd_data,
                    'atr': atr,
                    'volume_ratio': volume_data['volume_ratio'],
                    'trend': trend
                }}
            }}
        else:
            return {{
                'action': 'HOLD',
                'symbol': '{symbol}',
                'current_price': current_price,
                'confidence': 0.5,
                'reasons': ['Insufficient signals for entry'],
                'technical_data': {{
                    'rsi': rsi,
                    'macd': macd_data,
                    'atr': atr,
                    'volume_ratio': volume_data['volume_ratio'],
                    'trend': trend
                }}
            }}
    
    except Exception as e:
        return {{
            'action': 'HOLD',
            'reason': f'Analysis error: {{str(e)}}',
            'error': True
        }}

# Execute analysis
result = make_trading_decision()
print(json.dumps(result, indent=2))
'''
        return script
    
    async def execute_claude_code(self, script: str) -> Dict[str, Any]:
        """
        Execute Python script using Claude Code
        
        Args:
            script: Python script to execute
            
        Returns:
            Execution result
        """
        for attempt in range(self.max_retries):
            try:
                # Create temporary file for the script
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(script)
                    script_path = f.name
                
                try:
                    # Execute using claude-code CLI
                    cmd = ['claude-code', 'run', script_path]
                    
                    logger.info(f"Executing Claude Code (attempt {attempt + 1})")
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=self.timeout
                    )
                    
                    if process.returncode == 0:
                        output = stdout.decode('utf-8').strip()
                        try:
                            result = json.loads(output)
                            logger.info("Claude Code execution successful")
                            return result
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON output: {output}")
                            return {
                                'action': 'HOLD',
                                'reason': 'Failed to parse analysis result',
                                'raw_output': output
                            }
                    else:
                        error_msg = stderr.decode('utf-8')
                        logger.error(f"Claude Code execution failed: {error_msg}")
                        
                        if attempt == self.max_retries - 1:
                            return {
                                'action': 'HOLD',
                                'reason': f'Execution failed: {error_msg}',
                                'error': True
                            }
                
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(script_path)
                    except:
                        pass
                        
            except asyncio.TimeoutError:
                logger.error(f"Claude Code execution timeout (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return {
                        'action': 'HOLD',
                        'reason': 'Execution timeout',
                        'error': True
                    }
            except Exception as e:
                logger.error(f"Claude Code execution error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    return {
                        'action': 'HOLD',
                        'reason': f'Execution error: {str(e)}',
                        'error': True
                    }
            
            # Wait before retry
            await asyncio.sleep(2 ** attempt)
        
        return {
            'action': 'HOLD',
            'reason': 'Max retries exceeded',
            'error': True
        }
    
    async def analyze_trading_opportunity(self, symbol: str, market_data: Dict) -> Dict[str, Any]:
        """
        Analyze trading opportunity using Claude Code
        
        Args:
            symbol: Trading symbol
            market_data: Market data for analysis
            
        Returns:
            Trading analysis result
        """
        try:
            logger.info(f"Starting trading analysis for {symbol}")
            
            # Create analysis script
            script = await self.create_trading_analysis_script(symbol, market_data)
            
            # Execute script in Claude Code
            result = await self.execute_claude_code(script)
            
            # Add metadata
            result['timestamp'] = datetime.now().isoformat()
            result['symbol'] = symbol
            
            logger.info(f"Analysis complete for {symbol}: {result.get('action', 'UNKNOWN')}")
            return result
            
        except Exception as e:
            logger.error(f"Error in trading analysis for {symbol}: {e}")
            return {
                'action': 'HOLD',
                'symbol': symbol,
                'reason': f'Analysis error: {str(e)}',
                'error': True,
                'timestamp': datetime.now().isoformat()
            }
    
    async def create_position_monitoring_script(self, symbol: str, position_data: Dict, 
                                              market_data: Dict) -> str:
        """
        Create script for monitoring existing position and adjusting TP/SL
        
        Args:
            symbol: Trading symbol
            position_data: Current position information
            market_data: Current market data
            
        Returns:
            Python script for position monitoring
        """
        script = f'''
import json
import numpy as np
import pandas as pd
from datetime import datetime

# Position and market data for {symbol}
position_data = {json.dumps(position_data, indent=2)}
market_data = {json.dumps(market_data, indent=2)}

def calculate_atr(highs, lows, closes, period=14):
    """Calculate Average True Range"""
    high_low = np.array(highs) - np.array(lows)
    high_close = np.abs(np.array(highs) - np.roll(closes, 1))
    low_close = np.abs(np.array(lows) - np.roll(closes, 1))
    
    true_ranges = np.maximum(high_low, np.maximum(high_close, low_close))
    atr = pd.Series(true_ranges).rolling(window=period).mean()
    return atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0

def calculate_trailing_stop(entry_price, current_price, side, atr, multiplier=2):
    """Calculate trailing stop loss"""
    if side.upper() == 'BUY':
        # For long positions
        trailing_stop = current_price - (atr * multiplier)
        return max(trailing_stop, entry_price - (atr * multiplier))
    else:
        # For short positions (if applicable)
        trailing_stop = current_price + (atr * multiplier)
        return min(trailing_stop, entry_price + (atr * multiplier))

def monitor_position():
    """Monitor position and suggest TP/SL adjustments"""
    try:
        # Extract current market data
        klines = market_data.get('kline_data', {{}}).get('result', {{}}).get('list', [])
        if not klines:
            return {{'action': 'HOLD', 'reason': 'No market data available'}}
        
        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        
        current_price = closes[-1]
        atr = calculate_atr(highs, lows, closes)
        
        # Extract position information
        entry_price = position_data.get('entry_price', current_price)
        current_qty = position_data.get('size', 0)
        side = position_data.get('side', 'Buy')
        current_pnl = position_data.get('unrealised_pnl', 0)
        
        # Calculate profit percentage
        if side.upper() == 'BUY':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        # Dynamic TP/SL adjustment logic
        suggestions = []
        
        # Trailing stop loss
        new_stop_loss = calculate_trailing_stop(entry_price, current_price, side, atr)
        
        # Take profit adjustment based on momentum
        if profit_pct > 5:  # If already 5% in profit
            # Adjust take profit higher to capture more gains
            if side.upper() == 'BUY':
                new_take_profit = current_price + (atr * 3)
            else:
                new_take_profit = current_price - (atr * 3)
            
            suggestions.append({{
                'action': 'ADJUST_TP',
                'new_take_profit': new_take_profit,
                'reason': 'Position in profit, extending take profit'
            }})
        
        # Stop loss adjustment
        if profit_pct > 2:  # Move to breakeven if 2% in profit
            if side.upper() == 'BUY':
                breakeven_stop = entry_price + (entry_price * 0.001)  # Small buffer
            else:
                breakeven_stop = entry_price - (entry_price * 0.001)
            
            suggestions.append({{
                'action': 'ADJUST_SL',
                'new_stop_loss': breakeven_stop,
                'reason': 'Moving stop loss to breakeven'
            }})
        elif profit_pct > 0:  # Trailing stop if in profit
            suggestions.append({{
                'action': 'ADJUST_SL',
                'new_stop_loss': new_stop_loss,
                'reason': 'Trailing stop loss'
            }})
        
        # Exit conditions
        if profit_pct < -5:  # Stop loss hit
            suggestions.append({{
                'action': 'EXIT',
                'reason': 'Stop loss threshold reached'
            }})
        elif profit_pct > 10:  # Take profit hit
            suggestions.append({{
                'action': 'EXIT',
                'reason': 'Take profit threshold reached'
            }})
        
        return {{
            'symbol': '{symbol}',
            'current_price': current_price,
            'entry_price': entry_price,
            'profit_pct': profit_pct,
            'current_pnl': current_pnl,
            'atr': atr,
            'suggestions': suggestions,
            'timestamp': datetime.now().isoformat()
        }}
    
    except Exception as e:
        return {{
            'action': 'HOLD',
            'reason': f'Monitoring error: {{str(e)}}',
            'error': True
        }}

# Execute monitoring
result = monitor_position()
print(json.dumps(result, indent=2))
'''
        return script
    
    async def monitor_position(self, symbol: str, position_data: Dict, 
                             market_data: Dict) -> Dict[str, Any]:
        """
        Monitor existing position and get TP/SL adjustment suggestions
        
        Args:
            symbol: Trading symbol
            position_data: Current position data
            market_data: Current market data
            
        Returns:
            Position monitoring result with suggestions
        """
        try:
            logger.info(f"Monitoring position for {symbol}")
            
            # Create monitoring script
            script = await self.create_position_monitoring_script(symbol, position_data, market_data)
            
            # Execute script
            result = await self.execute_claude_code(script)
            
            logger.info(f"Position monitoring complete for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Error monitoring position for {symbol}: {e}")
            return {
                'action': 'HOLD',
                'symbol': symbol,
                'reason': f'Monitoring error: {str(e)}',
                'error': True,
                'timestamp': datetime.now().isoformat()
            }
