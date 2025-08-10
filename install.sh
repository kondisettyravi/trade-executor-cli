#!/bin/bash

# Trade Executor CLI Installation Script

set -e

echo "🚀 Installing Trade Executor CLI..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python 3.9 or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Install the CLI tool in development mode
echo "🛠️  Installing Trade Executor CLI..."
pip install -e .

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p data logs config/prompts

# Copy example environment file if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API credentials before running the tool"
fi

echo ""
echo "🎉 Installation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API credentials"
echo "2. Validate configuration: trade-executor config --validate"
echo "3. Start trading: trade-executor start"
echo ""
echo "For help: trade-executor --help"
echo ""
echo "⚠️  IMPORTANT: Start with paper trading mode first!"
echo "   trade-executor start --paper"
