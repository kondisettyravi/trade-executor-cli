"""
Test script for MCP integration and trading bot functionality
"""
import asyncio
import json
import logging
from mcp_client import use_mcp_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_trending_coins():
    """Test trending coins functionality"""
    print("\n=== Testing Trending Coins ===")
    
    result = await use_mcp_tool("bybit", "get_trending_coins", {
        "category": "spot",
        "sortBy": "price_change_24h",
        "direction": "upward",
        "limit": 5
    })
    
    print(f"Trending coins result: {json.dumps(result, indent=2)}")
    return result

async def test_technical_analysis():
    """Test technical analysis tools"""
    print("\n=== Testing Technical Analysis ===")
    
    symbol = "BTCUSDT"
    
    # Test RSI
    print(f"\n--- RSI Analysis for {symbol} ---")
    rsi_result = await use_mcp_tool("bybit", "calculate_rsi", {
        "category": "spot",
        "symbol": symbol,
        "interval": "60",
        "period": 14
    })
    print(f"RSI: {rsi_result.get('rsi', 'N/A')}")
    print(f"Signal: {rsi_result.get('signal', 'N/A')}")
    
    # Test Multi-timeframe momentum
    print(f"\n--- Multi-timeframe Momentum for {symbol} ---")
    momentum_result = await use_mcp_tool("bybit", "scan_multi_timeframe_momentum", {
        "category": "spot",
        "symbol": symbol,
        "timeframes": ["15", "60", "240", "D"]
    })
    print(f"Overall Momentum: {momentum_result.get('overallMomentum', 'N/A')}")
    
    confluence = momentum_result.get('confluenceAnalysis', {})
    print(f"Bullish Timeframes: {confluence.get('bullishTimeframes', 0)}")
    print(f"Bearish Timeframes: {confluence.get('bearishTimeframes', 0)}")
    
    recommendation = momentum_result.get('tradingRecommendation', {})
    print(f"Recommendation: {recommendation.get('action', 'N/A')} (Confidence: {recommendation.get('confidence', 0)}%)")
    
    # Test MACD
    print(f"\n--- MACD Analysis for {symbol} ---")
    macd_result = await use_mcp_tool("bybit", "calculate_macd", {
        "category": "spot",
        "symbol": symbol,
        "interval": "60"
    })
    print(f"MACD: {macd_result.get('macd', 'N/A')}")
    print(f"Signal: {macd_result.get('signal', 'N/A')}")
    print(f"Signals: {macd_result.get('signals', [])}")
    
    return {
        'rsi': rsi_result,
        'momentum': momentum_result,
        'macd': macd_result
    }

async def test_trading_operations():
    """Test trading-related operations"""
    print("\n=== Testing Trading Operations ===")
    
    symbol = "BTCUSDT"
    
    # Test wallet balance
    print("\n--- Wallet Balance ---")
    balance_result = await use_mcp_tool("bybit", "get_wallet_balance", {
        "accountType": "UNIFIED"
    })
    print(f"Balance result: {json.dumps(balance_result, indent=2)}")
    
    # Test ticker
    print(f"\n--- Ticker for {symbol} ---")
    ticker_result = await use_mcp_tool("bybit", "get_tickers", {
        "category": "spot",
        "symbol": symbol
    })
    
    if ticker_result and 'result' in ticker_result:
        ticker_data = ticker_result['result']['list'][0]
        print(f"Current Price: {ticker_data['lastPrice']}")
        print(f"24h Change: {ticker_data['priceChangePercent24h']}%")
    
    # Test position sizing
    print(f"\n--- Position Sizing for {symbol} ---")
    position_size_result = await use_mcp_tool("bybit", "calculate_position_size", {
        "category": "spot",
        "symbol": symbol,
        "accountBalance": 10000,
        "riskPercentage": 2,
        "stopLossPrice": 118000,
        "currentPrice": 119000
    })
    print(f"Recommended Size: {position_size_result.get('recommendedSize', 'N/A')}")
    print(f"Risk Amount: {position_size_result.get('riskAmount', 'N/A')}")
    
    return {
        'balance': balance_result,
        'ticker': ticker_result,
        'position_size': position_size_result
    }

async def test_complete_analysis():
    """Test complete trading analysis workflow"""
    print("\n=== Testing Complete Analysis Workflow ===")
    
    # Get trending coins
    trending_result = await test_trending_coins()
    
    if trending_result and 'trending' in trending_result:
        # Pick first trending coin
        symbol = trending_result['trending'][0]['symbol']
        print(f"\nAnalyzing trending coin: {symbol}")
        
        # Run technical analysis
        ta_results = await test_technical_analysis()
        
        # Simulate trading decision
        rsi = ta_results['rsi'].get('rsi', 50)
        momentum = ta_results['momentum'].get('overallMomentum', 'neutral')
        macd_signals = ta_results['macd'].get('signals', [])
        
        signals = []
        confidence = 0
        
        # RSI signals
        if rsi < 30:
            signals.append(('BUY', f'RSI oversold at {rsi:.2f}'))
            confidence += 0.25
        elif rsi > 70:
            signals.append(('SELL', f'RSI overbought at {rsi:.2f}'))
            confidence += 0.25
        
        # Momentum signals
        if momentum == 'bullish':
            signals.append(('BUY', 'Bullish momentum'))
            confidence += 0.3
        elif momentum == 'bearish':
            signals.append(('SELL', 'Bearish momentum'))
            confidence += 0.3
        
        # MACD signals
        if 'bullish_crossover' in macd_signals:
            signals.append(('BUY', 'MACD bullish crossover'))
            confidence += 0.2
        elif 'bearish_crossover' in macd_signals:
            signals.append(('SELL', 'MACD bearish crossover'))
            confidence += 0.2
        
        # Make decision
        buy_signals = [s for s in signals if s[0] == 'BUY']
        sell_signals = [s for s in signals if s[0] == 'SELL']
        
        print(f"\n--- Trading Decision for {symbol} ---")
        print(f"All signals: {signals}")
        print(f"Buy signals: {len(buy_signals)}")
        print(f"Sell signals: {len(sell_signals)}")
        print(f"Confidence: {confidence:.2f}")
        
        if len(buy_signals) >= 2 and confidence >= 0.4:
            action = "BUY"
            print(f"🟢 DECISION: {action} - Strong bullish signals")
        elif len(sell_signals) >= 2 and confidence >= 0.4:
            action = "SELL"
            print(f"🔴 DECISION: {action} - Strong bearish signals")
        else:
            action = "HOLD"
            print(f"🟡 DECISION: {action} - Insufficient signals")
        
        return {
            'symbol': symbol,
            'action': action,
            'confidence': confidence,
            'signals': signals
        }

async def main():
    """Main test function"""
    print("🚀 Starting MCP Integration Tests")
    
    try:
        # Test individual components
        await test_trending_coins()
        await test_technical_analysis()
        await test_trading_operations()
        
        # Test complete workflow
        final_result = await test_complete_analysis()
        
        print("\n" + "="*50)
        print("✅ All tests completed successfully!")
        print(f"Final analysis result: {json.dumps(final_result, indent=2)}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
