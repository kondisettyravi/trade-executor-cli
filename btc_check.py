#!/usr/bin/env python3
import os
import sys
import json
import requests
import time
import hmac
import hashlib
import urllib.parse
from datetime import datetime

# Try to import from config file first, then fall back to environment variables
try:
    from config import BYBIT_API_KEY, BYBIT_API_SECRET
    api_key = BYBIT_API_KEY
    api_secret = BYBIT_API_SECRET
except ImportError:
    # Fall back to environment variables
    api_key = os.environ.get('BYBIT_API_KEY')
    api_secret = os.environ.get('BYBIT_API_SECRET')

if not api_key or not api_secret:
    print("Error: API keys not found in config.py or environment variables")
    sys.exit(1)

# Bybit API endpoint
endpoint = 'https://api.bybit.com'

# Function to generate signature
def generate_signature(secret, params):
    sorted_params = sorted(params.items())
    signature_payload = '&'.join([f"{key}={value}" for key, value in sorted_params])
    return hmac.new(secret.encode(), signature_payload.encode(), hashlib.sha256).hexdigest()

# Function to make authenticated GET request
def make_authenticated_request(path, params=None):
    url = f"{endpoint}{path}"
    timestamp = int(time.time() * 1000)
    
    if params is None:
        params = {}
    
    params['api_key'] = api_key
    params['timestamp'] = str(timestamp)
    params['recv_window'] = '5000'
    
    signature = generate_signature(api_secret, params)
    params['sign'] = signature
    
    response = requests.get(url, params=params)
    return response.json()

# Get position information
def get_position():
    path = '/v5/position/list'
    params = {
        'category': 'linear',
        'symbol': 'BTCUSDT'
    }
    return make_authenticated_request(path, params)

# Get current market price
def get_market_price():
    path = '/v5/market/tickers'
    params = {
        'category': 'linear',
        'symbol': 'BTCUSDT'
    }
    return make_authenticated_request(path, params)

# Main function
def main():
    try:
        # Get position data
        position_data = get_position()
        
        if position_data['retCode'] != 0:
            print(f"Error getting position: {position_data['retMsg']}")
            return
        
        positions = position_data['result']['list']
        
        if not positions:
            print("No BTC position found")
            return
        
        position = positions[0]
        
        # Get current market price
        price_data = get_market_price()
        
        if price_data['retCode'] != 0:
            print(f"Error getting market price: {price_data['retMsg']}")
            return
        
        current_price = float(price_data['result']['list'][0]['lastPrice'])
        
        # Calculate position details
        entry_price = float(position['avgPrice'])
        size = float(position['size'])
        side = position['side']
        unrealized_pnl = float(position['unrealisedPnl'])
        stop_loss = float(position['stopLoss']) if position['stopLoss'] else None
        take_profit = float(position['takeProfit']) if position['takeProfit'] else None
        
        # Calculate percentage profit/loss
        if side == 'Buy':
            pnl_percentage = ((current_price - entry_price) / entry_price) * 100
        else:
            pnl_percentage = ((entry_price - current_price) / entry_price) * 100
        
        # Print position information
        print(f"BTC Position:")
        print(f"  Side: {side}")
        print(f"  Size: {size}")
        print(f"  Entry Price: ${entry_price:.2f}")
        print(f"  Current Price: ${current_price:.2f}")
        print(f"  Unrealized P&L: ${unrealized_pnl:.2f} ({pnl_percentage:.2f}%)")
        
        if stop_loss:
            sl_distance = abs(current_price - stop_loss)
            sl_percentage = (sl_distance / current_price) * 100
            print(f"  Stop Loss: ${stop_loss:.2f} ({sl_percentage:.2f}% away)")
        
        if take_profit:
            tp_distance = abs(take_profit - current_price)
            tp_percentage = (tp_distance / current_price) * 100
            print(f"  Take Profit: ${take_profit:.2f} ({tp_percentage:.2f}% away)")
        
        # Alert if close to stop loss or take profit
        if stop_loss and (abs(current_price - stop_loss) / current_price) * 100 < 0.3:
            print("⚠️ WARNING: Price is very close to stop loss!")
        
        if take_profit and (abs(current_price - take_profit) / current_price) * 100 < 0.3:
            print("🎯 ALERT: Price is very close to take profit!")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()