#!/bin/bash

echo "Starting BTC position monitoring..."
echo "Press Ctrl+C to stop monitoring"

while true; do
  echo "========================================="
  echo "Checking position at $(date)"
  claude-code btc-check
  sleep 60
done