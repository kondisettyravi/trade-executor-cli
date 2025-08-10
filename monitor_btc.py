#!/usr/bin/env python3
import os
import sys
import json
import time
from datetime import datetime
import subprocess
import requests

# Position details
symbol = "BTCUSDT"
entry_price = 118770.9
stop_loss = 117500
take_profit = 121000
position_size = 0.001

# Monitoring settings
check_interval = 60  # seconds

def get_position_data():
    """Get BTC position data using curl command"""
    try:
        # Execute the claude-code command to get position data
        result = subprocess.run(
            ['claude-code', 'mcp__bybit-node__get_positions', '--category', 'linear', '--symbol', 'BTCUSDT'],
            capture_output=True, text=True, check=True
        )
        
        # Parse the JSON output
        data = json.loads(result.stdout)
        
        if data.get("retCode") != 0:
            print(f"Error: {data.get('retMsg')}")
            return None
        
        positions = data["result"]["list"]
        if not positions:
            print("No BTC position found")
            return None
        
        return positions[0]
    except subprocess.CalledProcessError as e:
        print(f"Command execution error: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_market_data():
    """Get BTC market data using curl command"""
    try:
        # Execute the claude-code command to get ticker data
        result = subprocess.run(
            ['claude-code', 'mcp__bybit-node__get_tickers', '--category', 'linear', '--symbol', 'BTCUSDT'],
            capture_output=True, text=True, check=True
        )
        
        # Parse the JSON output
        data = json.loads(result.stdout)
        
        if data.get("retCode") != 0:
            print(f"Error: {data.get('retMsg')}")
            return None
        
        tickers = data["result"]["list"]
        if not tickers:
            print("No BTC ticker data found")
            return None
        
        return tickers[0]
    except subprocess.CalledProcessError as e:
        print(f"Command execution error: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def monitor_position():
    """Monitor BTC position and market conditions"""
    print("Starting BTC position monitoring...")
    print(f"Entry Price: ${entry_price}")
    print(f"Stop Loss: ${stop_loss}")
    print(f"Take Profit: ${take_profit}")
    print(f"Position Size: {position_size} BTC")
    print(f"Monitoring every {check_interval} seconds...")
    print("")
    
    try:
        while True:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"=== Position Check at {now} ===")
            
            # Get position data
            position = get_position_data()
            if not position:
                print("Could not retrieve position data")
                continue
            
            # Get market data
            market = get_market_data()
            if not market:
                print("Could not retrieve market data")
                continue
            
            # Extract relevant data
            current_price = float(market["lastPrice"])
            unrealized_pnl = float(position["unrealisedPnl"])
            side = position["side"]
            
            # Calculate percentage profit/loss
            if side == "Buy":
                pnl_percentage = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_percentage = ((entry_price - current_price) / entry_price) * 100
            
            # Print position status
            print(f"Current Price: ${current_price}")
            print(f"Unrealized P&L: ${unrealized_pnl:.4f} ({pnl_percentage:.2f}%)")
            
            # Check proximity to stop loss / take profit
            sl_distance = abs(current_price - stop_loss)
            sl_percentage = (sl_distance / current_price) * 100
            print(f"Distance to Stop Loss: ${sl_distance:.2f} ({sl_percentage:.2f}%)")
            
            tp_distance = abs(take_profit - current_price)
            tp_percentage = (tp_distance / current_price) * 100
            print(f"Distance to Take Profit: ${tp_distance:.2f} ({tp_percentage:.2f}%)")
            
            # Alert if close to stop loss or take profit
            if sl_percentage < 0.3:
                print("⚠️ WARNING: Price is very close to stop loss!")
            
            if tp_percentage < 0.3:
                print("🎯 ALERT: Price is very close to take profit!")
            
            print("")  # Empty line for readability
            
            # Wait for next check
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")

if __name__ == "__main__":
    monitor_position()