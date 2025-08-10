#!/bin/bash

# Trade Executor CLI Activation Script
# This script activates the virtual environment and provides helpful commands

echo "🔧 Activating Trade Executor CLI virtual environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo ""
echo "Available commands:"
echo "  trade-executor setup-bedrock    # Setup AWS Bedrock API key"
echo "  trade-executor config --validate # Validate configuration"
echo "  trade-executor start --demo     # Start with demo mode (safe)"
echo "  trade-executor dashboard        # Live monitoring dashboard"
echo "  trade-executor --help           # Show all commands"
echo ""
echo "To deactivate later, run: deactivate"
echo ""

# Start a new shell with the virtual environment activated
exec "$SHELL"
