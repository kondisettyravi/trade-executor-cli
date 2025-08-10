"""Live trading dashboard with real-time updates."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.text import Text
from rich.align import Align
import structlog

logger = structlog.get_logger(__name__)


class TradingDashboard:
    """Live trading dashboard with real-time updates."""
    
    def __init__(self, trading_engine):
        self.trading_engine = trading_engine
        self.console = Console()
        self.layout = Layout()
        self.is_running = False
        
        # Setup layout
        self._setup_layout()
    
    def _setup_layout(self):
        """Setup the dashboard layout."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        self.layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        self.layout["left"].split_column(
            Layout(name="session_info", size=8),
            Layout(name="current_trade", size=10),
            Layout(name="risk_status", size=8)
        )
        
        self.layout["right"].split_column(
            Layout(name="market_data", size=12),
            Layout(name="news_sentiment", size=6),
            Layout(name="performance", size=8)
        )
    
    async def run(self):
        """Run the live dashboard."""
        self.is_running = True
        
        with Live(self.layout, console=self.console, refresh_per_second=2) as live:
            while self.is_running:
                try:
                    await self._update_dashboard()
                    await asyncio.sleep(5)  # Update every 5 seconds
                except KeyboardInterrupt:
                    self.is_running = False
                    break
                except Exception as e:
                    logger.error("Dashboard update error", error=str(e))
                    await asyncio.sleep(5)
    
    async def _update_dashboard(self):
        """Update all dashboard components."""
        try:
            # Get current status
            status = await self.trading_engine.get_session_status()
            
            # Update header
            self._update_header()
            
            # Update main sections
            self._update_session_info(status)
            self._update_current_trade(status)
            self._update_risk_status()
            self._update_market_data(status)
            self._update_news_sentiment(status)
            await self._update_performance()
            
            # Update footer
            self._update_footer()
            
        except Exception as e:
            logger.error("Failed to update dashboard", error=str(e))
    
    def _update_header(self):
        """Update the header section."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header_text = Text.assemble(
            ("🤖 ", "bold blue"),
            ("Trade Executor Dashboard", "bold white"),
            ("  |  ", "dim"),
            (current_time, "cyan")
        )
        
        self.layout["header"].update(
            Panel(
                Align.center(header_text),
                style="bold blue"
            )
        )
    
    def _update_session_info(self, status: Dict[str, Any]):
        """Update session information panel."""
        if not status.get("active"):
            session_panel = Panel(
                Align.center(Text("No Active Session", style="yellow bold")),
                title="Session Status",
                border_style="yellow"
            )
        else:
            session_table = Table(show_header=False, box=None)
            session_table.add_column("Property", style="cyan")
            session_table.add_column("Value", style="white")
            
            session_table.add_row("Status", "🟢 Active")
            session_table.add_row("Session ID", status["session_id"][:8] + "...")
            session_table.add_row("Started", status["session_start"][:19])
            
            session_panel = Panel(
                session_table,
                title="Session Info",
                border_style="green"
            )
        
        self.layout["session_info"].update(session_panel)
    
    def _update_current_trade(self, status: Dict[str, Any]):
        """Update current trade panel."""
        current_trade = status.get("current_trade")
        
        if not current_trade:
            trade_panel = Panel(
                Align.center(Text("No Active Trade", style="dim")),
                title="Current Trade",
                border_style="dim"
            )
        else:
            trade_table = Table(show_header=False, box=None)
            trade_table.add_column("Property", style="cyan")
            trade_table.add_column("Value", style="white")
            
            # Trade status color
            status_color = {
                "active": "green",
                "pending": "yellow",
                "closed": "blue",
                "cancelled": "red",
                "error": "red"
            }.get(current_trade["status"], "white")
            
            trade_table.add_row("Symbol", current_trade["symbol"])
            trade_table.add_row("Side", current_trade["side"])
            trade_table.add_row("Status", f"[{status_color}]{current_trade['status'].upper()}[/{status_color}]")
            trade_table.add_row("Quantity", str(current_trade["quantity"]))
            trade_table.add_row("Entry Price", str(current_trade.get("entry_price", "N/A")))
            
            if current_trade.get("stop_loss"):
                trade_table.add_row("Stop Loss", str(current_trade["stop_loss"]))
            
            if current_trade.get("take_profit"):
                trade_table.add_row("Take Profit", str(current_trade["take_profit"]))
            
            trade_table.add_row("Confidence", f"{current_trade.get('confidence', 0):.1%}")
            
            trade_panel = Panel(
                trade_table,
                title="Current Trade",
                border_style="green" if current_trade["status"] == "active" else "yellow"
            )
        
        self.layout["current_trade"].update(trade_panel)
    
    def _update_risk_status(self):
        """Update risk status panel."""
        try:
            risk_status = self.trading_engine.risk_manager.get_risk_status()
            
            risk_table = Table(show_header=False, box=None)
            risk_table.add_column("Metric", style="cyan")
            risk_table.add_column("Value", style="white")
            
            # Risk level color
            risk_color = {
                "low": "green",
                "medium": "yellow",
                "high": "red",
                "critical": "red bold"
            }.get(risk_status["overall_risk_level"], "white")
            
            risk_table.add_row(
                "Risk Level", 
                f"[{risk_color}]{risk_status['overall_risk_level'].upper()}[/{risk_color}]"
            )
            risk_table.add_row("Can Trade", "✅" if risk_status["can_trade"] else "❌")
            risk_table.add_row("Daily Trades", f"{risk_status['daily_trades']}/3")
            risk_table.add_row("Daily P&L", f"${risk_status['daily_pnl']:.2f}")
            risk_table.add_row("Remaining Trades", str(risk_status["remaining_trades"]))
            
            if risk_status["emergency_stop_active"]:
                risk_table.add_row("Emergency Stop", "[red bold]ACTIVE[/red bold]")
            
            risk_panel = Panel(
                risk_table,
                title="Risk Status",
                border_style=risk_color
            )
            
        except Exception as e:
            risk_panel = Panel(
                Text(f"Error: {str(e)}", style="red"),
                title="Risk Status",
                border_style="red"
            )
        
        self.layout["risk_status"].update(risk_panel)
    
    def _update_market_data(self, status: Dict[str, Any]):
        """Update market data panel."""
        market_data = status.get("latest_market_data", {})
        
        if not market_data:
            market_panel = Panel(
                Align.center(Text("No Market Data", style="dim")),
                title="Market Data",
                border_style="dim"
            )
        else:
            market_table = Table(show_header=True, box=None)
            market_table.add_column("Symbol", style="cyan")
            market_table.add_column("Price", style="green")
            market_table.add_column("24h Change", style="white")
            market_table.add_column("Volume", style="yellow")
            
            for symbol, data in market_data.items():
                try:
                    ticker = data.get("ticker", {}).get("result", {}).get("list", [{}])[0]
                    if ticker:
                        price = ticker.get("lastPrice", "N/A")
                        change_24h = ticker.get("price24hPcnt", "0")
                        volume = ticker.get("volume24h", "N/A")
                        
                        # Format change with color
                        try:
                            change_float = float(change_24h) * 100
                            change_color = "green" if change_float > 0 else "red"
                            change_text = f"[{change_color}]{change_float:+.2f}%[/{change_color}]"
                        except:
                            change_text = "N/A"
                        
                        market_table.add_row(symbol, price, change_text, volume)
                except Exception:
                    market_table.add_row(symbol, "N/A", "N/A", "N/A")
            
            market_panel = Panel(
                market_table,
                title="Market Data",
                border_style="blue"
            )
        
        self.layout["market_data"].update(market_panel)
    
    def _update_news_sentiment(self, status: Dict[str, Any]):
        """Update news sentiment panel."""
        news_summary = status.get("latest_news_summary", {})
        
        if news_summary.get("status") == "no_data":
            news_panel = Panel(
                Align.center(Text("No News Data", style="dim")),
                title="News Sentiment",
                border_style="dim"
            )
        else:
            news_table = Table(show_header=False, box=None)
            news_table.add_column("Property", style="cyan")
            news_table.add_column("Value", style="white")
            
            sentiment = news_summary.get("sentiment", "neutral")
            sentiment_color = {
                "very_bullish": "green bold",
                "bullish": "green",
                "neutral": "yellow",
                "bearish": "red",
                "very_bearish": "red bold"
            }.get(sentiment, "white")
            
            news_table.add_row("Sentiment", f"[{sentiment_color}]{sentiment.upper()}[/{sentiment_color}]")
            news_table.add_row("Impact", news_summary.get("impact", "N/A"))
            news_table.add_row("Sources", str(news_summary.get("source_count", 0)))
            news_table.add_row("Updated", news_summary.get("timestamp", "N/A")[:19])
            
            news_panel = Panel(
                news_table,
                title="News Sentiment",
                border_style="blue"
            )
        
        self.layout["news_sentiment"].update(news_panel)
    
    async def _update_performance(self):
        """Update performance panel."""
        try:
            performance = await self.trading_engine.session_manager.get_performance_summary(7)  # Last 7 days
            
            if not performance or performance.get("total_trades", 0) == 0:
                perf_panel = Panel(
                    Align.center(Text("No Performance Data", style="dim")),
                    title="Performance (7d)",
                    border_style="dim"
                )
            else:
                perf_table = Table(show_header=False, box=None)
                perf_table.add_column("Metric", style="cyan")
                perf_table.add_column("Value", style="white")
                
                perf_table.add_row("Total Trades", str(performance["total_trades"]))
                perf_table.add_row("Win Rate", f"{performance['win_rate']:.1f}%")
                
                # P&L with color
                total_pnl = performance["total_pnl"]
                pnl_color = "green" if total_pnl > 0 else "red"
                perf_table.add_row("Total P&L", f"[{pnl_color}]${total_pnl:.2f}[/{pnl_color}]")
                
                perf_table.add_row("Best Trade", f"[green]${performance['best_trade']:.2f}[/green]")
                perf_table.add_row("Worst Trade", f"[red]${performance['worst_trade']:.2f}[/red]")
                
                perf_panel = Panel(
                    perf_table,
                    title="Performance (7d)",
                    border_style="green" if total_pnl > 0 else "red"
                )
            
        except Exception as e:
            perf_panel = Panel(
                Text(f"Error: {str(e)}", style="red"),
                title="Performance (7d)",
                border_style="red"
            )
        
        self.layout["performance"].update(perf_panel)
    
    def _update_footer(self):
        """Update the footer section."""
        footer_text = Text.assemble(
            ("Press ", "dim"),
            ("Ctrl+C", "bold red"),
            (" to exit  |  ", "dim"),
            ("Updates every 5 seconds", "dim"),
            ("  |  ", "dim"),
            ("🔄 Live Dashboard", "green")
        )
        
        self.layout["footer"].update(
            Panel(
                Align.center(footer_text),
                style="dim"
            )
        )


class SimpleDashboard:
    """Simplified dashboard for basic monitoring."""
    
    def __init__(self, trading_engine):
        self.trading_engine = trading_engine
        self.console = Console()
    
    async def show_status(self):
        """Show current status in a simple format."""
        try:
            status = await self.trading_engine.get_session_status()
            
            self.console.print("\n" + "="*60)
            self.console.print("[bold blue]Trading Status Update[/bold blue]")
            self.console.print("="*60)
            
            if not status.get("active"):
                self.console.print("[yellow]No active trading session[/yellow]")
                return
            
            # Session info
            self.console.print(f"[green]Session Active[/green] - ID: {status['session_id'][:8]}...")
            self.console.print(f"Started: {status['session_start'][:19]}")
            
            # Current trade
            current_trade = status.get("current_trade")
            if current_trade:
                self.console.print(f"\n[bold]Current Trade:[/bold]")
                self.console.print(f"  Symbol: {current_trade['symbol']}")
                self.console.print(f"  Side: {current_trade['side']}")
                self.console.print(f"  Status: {current_trade['status']}")
                self.console.print(f"  Entry: {current_trade.get('entry_price', 'N/A')}")
            else:
                self.console.print("\n[dim]No active trade[/dim]")
            
            # Risk status
            risk_status = self.trading_engine.risk_manager.get_risk_status()
            self.console.print(f"\n[bold]Risk Status:[/bold]")
            self.console.print(f"  Risk Level: {risk_status['overall_risk_level']}")
            self.console.print(f"  Daily Trades: {risk_status['daily_trades']}")
            self.console.print(f"  Daily P&L: ${risk_status['daily_pnl']:.2f}")
            
            self.console.print("="*60 + "\n")
            
        except Exception as e:
            self.console.print(f"[red]Error getting status: {e}[/red]")
