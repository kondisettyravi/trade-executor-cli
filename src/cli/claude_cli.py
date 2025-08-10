"""CLI interface for the Claude orchestrator."""

import asyncio
import sys
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import structlog

from ..core.claude_orchestrator import ClaudeOrchestrator

# Initialize console and logger
console = Console()
logger = structlog.get_logger(__name__)

# Create Typer app
app = typer.Typer(
    name="claude-trader",
    help="24/7 Claude Trading Orchestrator",
    rich_markup_mode="rich"
)


@app.command()
def start(
    interval: int = typer.Option(
        15, 
        "--interval", 
        "-i", 
        help="Monitoring interval in minutes"
    ),
    verbose: bool = typer.Option(
        False, 
        "--verbose", 
        "-v", 
        help="Enable verbose logging"
    )
):
    """Start 24/7 automated trading with Claude."""
    
    console.print(Panel.fit(
        "[bold blue]🚀 Starting 24/7 Claude Trading Orchestrator[/bold blue]",
        border_style="blue"
    ))
    
    console.print(f"[green]📊 Monitoring interval: {interval} minutes[/green]")
    console.print(f"[green]🤖 Using Claude CLI for all trading decisions[/green]")
    console.print(f"[yellow]Press Ctrl+C to stop[/yellow]\n")
    
    orchestrator = ClaudeOrchestrator()
    orchestrator.monitoring_interval = interval * 60
    
    async def run_orchestrator():
        try:
            await orchestrator.start_24_7_trading()
        except KeyboardInterrupt:
            console.print("\n[yellow]🛑 Orchestrator stopped by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]❌ Orchestrator error: {e}[/red]")
    
    asyncio.run(run_orchestrator())


@app.command()
def status():
    """Show orchestrator status."""
    
    orchestrator = ClaudeOrchestrator()
    status = orchestrator.get_status()
    
    # Create status table
    table = Table(title="Claude Trading Orchestrator Status", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Running", "🟢 Yes" if status["is_running"] else "🔴 No")
    table.add_row("Monitoring Interval", f"{status['monitoring_interval_minutes']} minutes")
    table.add_row("Total Trades", str(status["total_trades"]))
    table.add_row("Last Activity", status["last_activity"])
    
    if status["current_trade"]:
        trade = status["current_trade"]
        table.add_row("Current Trade", "🟢 Active")
        table.add_row("Trade Started", trade["initiated_at"])
        table.add_row("Last Monitored", trade["last_monitored"])
        table.add_row("Trade Status", trade["status"])
    else:
        table.add_row("Current Trade", "🔴 None")
    
    console.print(table)


@app.command()
def test():
    """Test Claude CLI integration."""
    
    console.print("[blue]🧪 Testing Claude CLI integration...[/blue]")
    
    orchestrator = ClaudeOrchestrator()
    
    async def run_test():
        try:
            # Test simple claude command
            result = await orchestrator._execute_claude_command("What is the current time?")
            
            if result:
                console.print("[green]✅ Claude CLI is working![/green]")
                console.print(f"[dim]Response length: {len(result)} characters[/dim]")
                console.print(f"[dim]First 200 chars: {result[:200]}...[/dim]")
            else:
                console.print("[red]❌ Claude CLI test failed[/red]")
                console.print("[yellow]Make sure 'claude' command is available in your PATH[/yellow]")
                
        except Exception as e:
            console.print(f"[red]❌ Test error: {e}[/red]")
    
    asyncio.run(run_test())


@app.command()
def simulate(
    cycles: int = typer.Option(
        3, 
        "--cycles", 
        "-c", 
        help="Number of monitoring cycles to simulate"
    )
):
    """Simulate trading cycles for testing."""
    
    console.print(f"[blue]🎭 Simulating {cycles} trading cycles...[/blue]")
    
    orchestrator = ClaudeOrchestrator()
    
    async def run_simulation():
        try:
            for i in range(cycles):
                console.print(f"\n[cyan]--- Cycle {i+1}/{cycles} ---[/cyan]")
                
                if not orchestrator.current_trade:
                    console.print("[yellow]📈 Initiating new trade...[/yellow]")
                    await orchestrator._initiate_new_trade()
                else:
                    console.print("[yellow]👁️ Monitoring current trade...[/yellow]")
                    await orchestrator._monitor_current_trade()
                
                if i < cycles - 1:
                    console.print("[dim]Waiting 10 seconds before next cycle...[/dim]")
                    await asyncio.sleep(10)
            
            console.print(f"\n[green]✅ Simulation completed![/green]")
            console.print(f"Total trades in history: {len(orchestrator.trade_history)}")
            
        except Exception as e:
            console.print(f"\n[red]❌ Simulation error: {e}[/red]")
    
    asyncio.run(run_simulation())


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of recent trades to show")
):
    """Show trading history from orchestrator."""
    
    orchestrator = ClaudeOrchestrator()
    
    if not orchestrator.trade_history:
        console.print("[yellow]No trading history found[/yellow]")
        return
    
    # Show recent trades
    recent_trades = orchestrator.trade_history[-limit:]
    
    table = Table(title="Claude Trading History", show_header=True, header_style="bold magenta")
    table.add_column("Date", style="cyan")
    table.add_column("Duration", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Monitoring Cycles", style="blue")
    
    for trade in recent_trades:
        duration = "N/A"
        if trade.get("completed_at") and trade.get("initiated_at"):
            start = trade["initiated_at"]
            end = trade["completed_at"]
            duration_delta = end - start
            duration = f"{duration_delta.total_seconds() / 3600:.1f}h"
        
        monitoring_cycles = "N/A"
        if trade.get("last_monitored") and trade.get("initiated_at"):
            # Estimate monitoring cycles based on time difference
            start = trade["initiated_at"]
            last = trade["last_monitored"]
            time_diff = (last - start).total_seconds()
            cycles = int(time_diff / (15 * 60)) + 1  # 15 min intervals
            monitoring_cycles = str(cycles)
        
        table.add_row(
            trade["initiated_at"].strftime("%Y-%m-%d %H:%M"),
            duration,
            trade["status"],
            monitoring_cycles
        )
    
    console.print(table)


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", help="Open config file for editing"),
    style: str = typer.Option(None, "--style", help="Set trading style (aggressive, moderate, cautious, conservative)"),
    coins: str = typer.Option(None, "--coins", help="Set coins to trade (comma-separated, e.g., BTC,ETH,SOL)"),
    interval: int = typer.Option(None, "--interval", help="Set monitoring interval in minutes")
):
    """Manage trading configuration."""
    
    orchestrator = ClaudeOrchestrator()
    
    if show:
        # Show current configuration
        config = orchestrator.config
        
        console.print(Panel.fit(
            "[bold blue]📋 Current Trading Configuration[/bold blue]",
            border_style="blue"
        ))
        
        # Trading settings
        trading = config['trading']
        console.print(f"[bold]Trading Style:[/bold] {trading['style']}")
        console.print(f"[bold]Coins:[/bold] {', '.join(trading['coins'])}")
        console.print(f"[bold]Position Size:[/bold] {trading['position_size']['min']}-{trading['position_size']['max']}%")
        console.print(f"[bold]Monitoring Interval:[/bold] {trading['monitoring_interval']} minutes")
        
        # Style description
        if trading['style'] in config['styles']:
            style_info = config['styles'][trading['style']]
            console.print(f"\n[bold]Style Description:[/bold]")
            console.print(f"  {style_info['description']}")
            console.print(f"  Risk Tolerance: {style_info['risk_tolerance']}")
            console.print(f"  Position Preference: {style_info['position_preference']}")
        
        # Advanced settings
        advanced = config['advanced']
        if advanced['additional_instructions']:
            console.print(f"\n[bold]Additional Instructions:[/bold] {advanced['additional_instructions']}")
        
        console.print(f"\n[bold]Completion Keywords:[/bold] {', '.join(advanced['completion_keywords'])}")
        
    elif edit:
        # Open config file for editing
        import subprocess
        config_path = "config/claude_trader.yaml"
        try:
            subprocess.run(["open", config_path])  # macOS
            console.print(f"[green]✅ Opened {config_path} for editing[/green]")
        except:
            try:
                subprocess.run(["code", config_path])  # VS Code
                console.print(f"[green]✅ Opened {config_path} in VS Code[/green]")
            except:
                console.print(f"[yellow]Please edit {config_path} manually[/yellow]")
    
    elif style or coins or interval:
        # Update specific settings
        import yaml
        config_path = "config/claude_trader.yaml"
        
        try:
            # Load current config
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update settings
            if style:
                if style not in ['aggressive', 'moderate', 'cautious', 'conservative']:
                    console.print("[red]❌ Invalid style. Choose: aggressive, moderate, cautious, conservative[/red]")
                    return
                config['trading']['style'] = style
                console.print(f"[green]✅ Trading style set to: {style}[/green]")
            
            if coins:
                coin_list = [coin.strip().upper() for coin in coins.split(',')]
                config['trading']['coins'] = coin_list
                console.print(f"[green]✅ Coins set to: {', '.join(coin_list)}[/green]")
            
            if interval:
                if interval < 1 or interval > 60:
                    console.print("[red]❌ Interval must be between 1 and 60 minutes[/red]")
                    return
                config['trading']['monitoring_interval'] = interval
                console.print(f"[green]✅ Monitoring interval set to: {interval} minutes[/green]")
            
            # Save updated config
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            console.print(f"[green]✅ Configuration updated in {config_path}[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Failed to update config: {e}[/red]")
    
    else:
        console.print("[yellow]Use --show to view config, --edit to edit, or specify settings to update[/yellow]")
        console.print("[dim]Examples:[/dim]")
        console.print("[dim]  claude-trader config --show[/dim]")
        console.print("[dim]  claude-trader config --style aggressive[/dim]")
        console.print("[dim]  claude-trader config --coins BTC,ETH,SOL[/dim]")
        console.print("[dim]  claude-trader config --interval 10[/dim]")


@app.callback()
def main():
    """
    Claude Trading Orchestrator
    
    24/7 automated trading system that uses the Claude CLI command
    for all trading decisions and monitoring.
    """
    pass


def cli_main():
    """Entry point for the Claude CLI application."""
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
