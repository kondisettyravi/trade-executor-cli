#!/usr/bin/env python3
"""
Environment Setup Script - Configure API credentials and environment variables
"""
import os
import json
from pathlib import Path

def create_env_file():
    """Create .env file with API credentials"""
    print("🔧 Setting up environment variables for Crypto Trading Bot")
    print("=" * 60)
    
    env_file = Path(".env")
    
    # Check if .env already exists
    if env_file.exists():
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return
    
    print("\n📝 Please provide your API credentials:")
    print("(Leave blank to skip - you can set these later)")
    
    # Get API credentials
    api_key = input("\nBybit API Key: ").strip()
    secret_key = input("Bybit Secret Key: ").strip()
    
    # Get Claude Code API key if needed
    claude_key = input("Claude Code API Key (optional): ").strip()
    
    # Create .env content
    env_content = f"""# Crypto Trading Bot Environment Variables
# Generated on {os.popen('date').read().strip()}

# Bybit API Credentials
BYBIT_API_KEY={api_key}
BYBIT_SECRET_KEY={secret_key}

# Claude Code API Key (if needed)
CLAUDE_CODE_API_KEY={claude_key}

# Trading Environment
TRADING_ENV=development
LOG_LEVEL=INFO

# Safety Settings
PAPER_TRADING=true
MAX_POSITION_SIZE_USD=100
"""
    
    # Write .env file
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Environment file created: {env_file}")
    print("\n🔒 Security Notes:")
    print("- Never commit .env file to version control")
    print("- Keep your API keys secure and private")
    print("- Use testnet/paper trading for initial testing")
    
    # Create .gitignore if it doesn't exist
    gitignore_file = Path(".gitignore")
    gitignore_content = """# Environment variables
.env
.env.local
.env.*.local

# Logs
*.log
logs/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Trading data
trading.log
performance_data/
"""
    
    if not gitignore_file.exists():
        with open(gitignore_file, 'w') as f:
            f.write(gitignore_content)
        print(f"✅ Created .gitignore file")

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        'anthropic',
        'requests', 
        'numpy',
        'pandas',
        'pytz'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies are installed!")
        return True

def validate_config():
    """Validate configuration file"""
    print("\n🔍 Validating configuration...")
    
    config_file = Path("config.json")
    if not config_file.exists():
        print("❌ config.json not found")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check required sections
        required_sections = ['trading', 'technical_analysis', 'bybit', 'safety']
        for section in required_sections:
            if section in config:
                print(f"✅ {section} section")
            else:
                print(f"❌ {section} section (missing)")
                return False
        
        # Check paper trading setting
        paper_trading = config.get('trading', {}).get('paper_trading', True)
        print(f"📊 Paper Trading: {'Enabled' if paper_trading else 'Disabled'}")
        
        if not paper_trading:
            print("⚠️  Real trading is enabled - ensure you have proper API credentials!")
        
        print("✅ Configuration is valid!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config.json: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Crypto Trading Bot Setup")
    print("=" * 40)
    
    # Step 1: Create environment file
    create_env_file()
    
    # Step 2: Check dependencies
    deps_ok = check_dependencies()
    
    # Step 3: Validate configuration
    config_ok = validate_config()
    
    print("\n" + "=" * 60)
    
    if deps_ok and config_ok:
        print("🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Review config.json settings")
        print("2. Test MCP integration: python test_mcp.py")
        print("3. Run the bot: python run_bot.py")
        print("\n⚠️  Start with paper trading enabled for testing!")
    else:
        print("❌ Setup incomplete - please fix the issues above")
    
    print("\n📚 Documentation:")
    print("- README.md - Main documentation")
    print("- INTEGRATION_GUIDE.md - Integration details")

if __name__ == "__main__":
    main()
