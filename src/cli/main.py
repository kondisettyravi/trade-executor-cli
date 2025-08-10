"""Main CLI interface for the automated crypto trading tool."""

import asyncio
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
import structlog

from ..core.config import ConfigManager
from ..core.trading_engine import TradingEngine
from ..integrations.mcp_client import mcp_client
from .dashboard import TradingDashboard

# Initialize console and logger
console = Console()
logger = structlog.get_logger(__name__)

# Create Typer app
app = typer.Typer(
    name="trade-executor",
    help="Automated cryptocurrency trading CLI powered by LLM",
    rich_markup_mode="rich"
)

# Global variables
config_manager = None
trading_engine = None


def initialize_app():
    """Initialize the application components."""
    global config_manager, trading_engine
    
    try:
        # Initialize configuration
        config_manager = ConfigManager()
        
        # Validate configuration
        config_errors = config_manager.validate_config()
        if config_errors:
            console.print("[red]Configuration errors found:[/red]")
            for error in config_errors:
                console.print(f"  • {error}")
            console.print("\n[yellow]Please fix these issues before running the trading engine.[/yellow]")
            raise typer.Exit(1)
        
        # Initialize trading engine with MCP client
        trading_engine = TradingEngine(config_manager, mcp_client)
        
        console.print("[green]✓[/green] Application initialized successfully")
        
    except Exception as e:
        console.print(f"[red]Failed to initialize application: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def start(
    paper_trading: bool = typer.Option(
        False, 
        "--paper", 
        help="Run in paper trading mode (no real trades)"
    ),
    verbose: bool = typer.Option(
        False, 
        "--verbose", 
        "-v", 
        help="Enable verbose logging"
    )
):
    """Start a new automated trading session."""
    
    if not trading_engine:
        initialize_app()
    
    console.print(Panel.fit(
        "[bold blue]🚀 Starting Automated Trading Session[/bold blue]",
        border_style="blue"
    ))
    
    if paper_trading:
        console.print("[yellow]⚠️  Paper trading mode enabled - no real trades will be executed[/yellow]")
    
    async def start_session():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Initializing trading session...", total=None)
                
                result = await trading_engine.start_trading_session()
                
                if "error" in result:
                    console.print(f"[red]❌ Failed to start session: {result['error']}[/red]")
                    return
                
                progress.update(task, description="Trading session started successfully!")
                progress.stop()
                
                console.print(f"[green]✅ Trading session started[/green]")
                console.print(f"Session ID: [cyan]{result['session_id']}[/cyan]")
                console.print("\n[yellow]💡 Use 'trade-executor dashboard' to monitor the session[/yellow]")
                console.print("[yellow]💡 Use 'trade-executor stop' to stop the session[/yellow]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Session startup cancelled by user[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Error starting session: {e}[/red]")
    
    asyncio.run(start_session())


@app.command()
def stop(
    emergency: bool = typer.Option(
        False, 
        "--emergency", 
        help="Emergency stop - immediately close all positions"
    )
):
    """Stop the current trading session."""
    
    if not trading_engine:
        initialize_app()
    
    if emergency:
        console.print("[red]🚨 Emergency stop initiated[/red]")
    else:
        console.print("[yellow]⏹️  Stopping trading session gracefully...[/yellow]")
    
    async def stop_session():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Stopping trading session...", total=None)
                
                result = await trading_engine.stop_trading_session(emergency=emergency)
                
                if "error" in result:
                    console.print(f"[red]❌ Failed to stop session: {result['error']}[/red]")
                    return
                
                progress.update(task, description="Trading session stopped successfully!")
                progress.stop()
                
                console.print(f"[green]✅ Trading session stopped[/green]")
                
        except Exception as e:
            console.print(f"[red]❌ Error stopping session: {e}[/red]")
    
    asyncio.run(stop_session())


@app.command()
def status():
    """Show current trading session status."""
    
    if not trading_engine:
        initialize_app()
    
    async def get_status():
        try:
            status = await trading_engine.get_session_status()
            
            if not status.get("active"):
                console.print("[yellow]No active trading session[/yellow]")
                return
            
            # Create status table
            table = Table(title="Trading Session Status", show_header=True, header_style="bold magenta")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Session ID", status["session_id"])
            table.add_row("Started", status["session_start"])
            table.add_row("Status", "🟢 Active" if status["active"] else "🔴 Inactive")
            
            if status.get("current_trade"):
                trade = status["current_trade"]
                table.add_row("Current Trade", f"{trade['symbol']} {trade['side']}")
                table.add_row("Trade Status", trade["status"])
                table.add_row("Entry Price", str(trade.get("entry_price", "N/A")))
                table.add_row("Quantity", str(trade["quantity"]))
            else:
                table.add_row("Current Trade", "None")
            
            console.print(table)
            
            # Show latest news summary
            news_summary = status.get("latest_news_summary", {})
            if news_summary.get("status") != "no_data":
                console.print(f"\n[bold]Latest News:[/bold] {news_summary.get('sentiment', 'N/A')} sentiment")
            
        except Exception as e:
            console.print(f"[red]❌ Error getting status: {e}[/red]")
    
    asyncio.run(get_status())


@app.command()
def dashboard():
    """Launch the live trading dashboard."""
    
    if not trading_engine:
        initialize_app()
    
    console.print("[blue]🎯 Launching trading dashboard...[/blue]")
    console.print("[dim]Press Ctrl+C to exit[/dim]\n")
    
    dashboard = TradingDashboard(trading_engine)
    
    try:
        asyncio.run(dashboard.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard closed by user[/yellow]")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent trades to show"),
    session_id: Optional[str] = typer.Option(None, "--session", help="Show trades for specific session")
):
    """Show trading history."""
    
    if not trading_engine:
        initialize_app()
    
    async def show_history():
        try:
            trades = await trading_engine.session_manager.get_trade_history(
                session_id=session_id, 
                limit=limit
            )
            
            if not trades:
                console.print("[yellow]No trading history found[/yellow]")
                return
            
            # Create history table
            table = Table(title="Trading History", show_header=True, header_style="bold magenta")
            table.add_column("Date", style="cyan")
            table.add_column("Symbol", style="yellow")
            table.add_column("Side", style="blue")
            table.add_column("Quantity", style="green")
            table.add_column("Entry Price", style="white")
            table.add_column("Status", style="magenta")
            table.add_column("P&L", style="red")
            
            for trade in trades:
                pnl_color = "green" if trade.get("pnl", 0) > 0 else "red"
                pnl_text = f"[{pnl_color}]{trade.get('pnl', 0):.2f}[/{pnl_color}]"
                
                table.add_row(
                    trade["created_at"][:10],  # Date only
                    trade["symbol"],
                    trade["side"],
                    str(trade["quantity"]),
                    str(trade.get("entry_price", "N/A")),
                    trade["status"],
                    pnl_text
                )
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Error getting history: {e}[/red]")
    
    asyncio.run(show_history())


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    validate: bool = typer.Option(False, "--validate", help="Validate configuration")
):
    """Manage configuration settings."""
    
    if not config_manager:
        initialize_app()
    
    if show:
        console.print("[bold blue]Current Configuration:[/bold blue]\n")
        
        # Trading config
        trading_config = config_manager.get_trading_config()
        console.print("[bold]Trading Settings:[/bold]")
        console.print(f"  Position sizes: {trading_config.position_sizes}%")
        console.print(f"  Max daily loss: {trading_config.max_daily_loss_percent}%")
        console.print(f"  Max position loss: {trading_config.max_position_loss_percent}%")
        console.print(f"  Max trades per day: {trading_config.max_trades_per_day}")
        console.print(f"  Allowed pairs: {', '.join(trading_config.allowed_pairs)}")
        
        # Bedrock config
        bedrock_config = config_manager.get_bedrock_config()
        console.print(f"\n[bold]AWS Bedrock Settings:[/bold]")
        console.print(f"  Region: {bedrock_config.region}")
        console.print(f"  Model: {bedrock_config.model_id}")
        console.print(f"  Temperature: {bedrock_config.temperature}")
        
        # Bybit config
        bybit_config = config_manager.get_bybit_config()
        console.print(f"\n[bold]Bybit Settings:[/bold]")
        console.print(f"  Category: {bybit_config.category}")
        console.print(f"  Testnet: {bybit_config.testnet}")
        console.print(f"  API Key: {'✓ Set' if bybit_config.api_key else '❌ Not set'}")
    
    if validate:
        console.print("[blue]Validating configuration...[/blue]")
        
        errors = config_manager.validate_config()
        if errors:
            console.print("[red]❌ Configuration errors found:[/red]")
            for error in errors:
                console.print(f"  • {error}")
        else:
            console.print("[green]✅ Configuration is valid[/green]")


@app.command()
def performance(
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze")
):
    """Show performance analytics."""
    
    if not trading_engine:
        initialize_app()
    
    async def show_performance():
        try:
            summary = await trading_engine.session_manager.get_performance_summary(days)
            
            if not summary or summary.get("total_trades", 0) == 0:
                console.print(f"[yellow]No trading data found for the last {days} days[/yellow]")
                return
            
            # Create performance table
            table = Table(title=f"Performance Summary ({days} days)", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Trades", str(summary["total_trades"]))
            table.add_row("Winning Trades", str(summary["winning_trades"]))
            table.add_row("Losing Trades", str(summary["losing_trades"]))
            table.add_row("Win Rate", f"{summary['win_rate']:.1f}%")
            
            pnl_color = "green" if summary["total_pnl"] > 0 else "red"
            table.add_row("Total P&L", f"[{pnl_color}]${summary['total_pnl']:.2f}[/{pnl_color}]")
            table.add_row("Average P&L", f"${summary['avg_pnl']:.2f}")
            table.add_row("Best Trade", f"[green]${summary['best_trade']:.2f}[/green]")
            table.add_row("Worst Trade", f"[red]${summary['worst_trade']:.2f}[/red]")
            
            console.print(table)
            
        except Exception as e:
            console.print(f"[red]❌ Error getting performance data: {e}[/red]")
    
    asyncio.run(show_performance())


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show version information")
):
    """
    Automated Cryptocurrency Trading CLI
    
    An intelligent trading system powered by AWS Bedrock LLM that automatically
    executes and manages cryptocurrency trades on Bybit exchange.
    """
    if version:
        console.print("[bold blue]Trade Executor CLI[/bold blue]")
        console.print("Version: 1.0.0")
        console.print("Author: AI Trading Systems")
        console.print("License: MIT")
        raise typer.Exit()


def cli_main():
    """Entry point for the CLI application."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
