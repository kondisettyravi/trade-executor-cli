"""Web dashboard for Claude Trading Orchestrator trade auditing."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import structlog
from flask import Flask, render_template, jsonify, request
import threading
import time

logger = structlog.get_logger(__name__)


class TradeAuditor:
    """Trade auditing system with SQLite database."""
    
    def __init__(self, db_path: str = "data/trades.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Ensure the data directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize the SQLite database with trade tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL,
                    style TEXT NOT NULL,
                    coins TEXT NOT NULL,
                    initiated_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_minutes INTEGER,
                    monitoring_cycles INTEGER DEFAULT 0,
                    initial_prompt TEXT,
                    initial_response TEXT,
                    final_response TEXT,
                    completion_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trade_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    update_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    claude_response TEXT,
                    analysis TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trade_id) REFERENCES trades (trade_id)
                )
            """)
            
            conn.commit()
            logger.info("✅ Trade audit database initialized", db_path=self.db_path)
    
    def log_trade_initiation(self, trade_data: Dict[str, Any]) -> str:
        """Log a new trade initiation."""
        trade_id = f"trade_{int(time.time())}_{hash(str(trade_data)) % 10000}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO trades (
                    trade_id, status, style, coins, initiated_at,
                    initial_prompt, initial_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_id,
                "active",
                trade_data.get("style", "unknown"),
                json.dumps(trade_data.get("coins", [])),
                trade_data.get("initiated_at", datetime.now()),
                trade_data.get("prompt", ""),
                trade_data.get("claude_response", "")
            ))
            
            # Log the initiation update
            conn.execute("""
                INSERT INTO trade_updates (
                    trade_id, update_type, timestamp, claude_response, analysis
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                trade_id,
                "initiation",
                trade_data.get("initiated_at", datetime.now()),
                trade_data.get("claude_response", ""),
                "Trade initiated successfully"
            ))
            
            conn.commit()
        
        logger.info("📊 Trade initiation logged", trade_id=trade_id)
        return trade_id
    
    def log_trade_update(self, trade_id: str, update_data: Dict[str, Any]):
        """Log a trade monitoring update."""
        with sqlite3.connect(self.db_path) as conn:
            # Update monitoring cycles count
            conn.execute("""
                UPDATE trades 
                SET monitoring_cycles = monitoring_cycles + 1
                WHERE trade_id = ?
            """, (trade_id,))
            
            # Log the update
            conn.execute("""
                INSERT INTO trade_updates (
                    trade_id, update_type, timestamp, claude_response, analysis
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                trade_id,
                "monitoring",
                update_data.get("timestamp", datetime.now()),
                update_data.get("claude_response", ""),
                update_data.get("analysis", "Trade monitoring update")
            ))
            
            conn.commit()
        
        logger.info("📈 Trade update logged", trade_id=trade_id)
    
    def log_trade_completion(self, trade_id: str, completion_data: Dict[str, Any]):
        """Log trade completion."""
        completed_at = completion_data.get("completed_at", datetime.now())
        
        with sqlite3.connect(self.db_path) as conn:
            # Get trade start time to calculate duration
            cursor = conn.execute(
                "SELECT initiated_at FROM trades WHERE trade_id = ?", 
                (trade_id,)
            )
            row = cursor.fetchone()
            
            duration_minutes = 0
            if row:
                initiated_at = datetime.fromisoformat(row[0])
                duration_minutes = int((completed_at - initiated_at).total_seconds() / 60)
            
            # Update trade completion
            conn.execute("""
                UPDATE trades 
                SET status = ?, completed_at = ?, duration_minutes = ?,
                    final_response = ?, completion_reason = ?
                WHERE trade_id = ?
            """, (
                "completed",
                completed_at,
                duration_minutes,
                completion_data.get("final_response", ""),
                completion_data.get("completion_reason", ""),
                trade_id
            ))
            
            # Log the completion update
            conn.execute("""
                INSERT INTO trade_updates (
                    trade_id, update_type, timestamp, claude_response, analysis
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                trade_id,
                "completion",
                completed_at,
                completion_data.get("final_response", ""),
                f"Trade completed: {completion_data.get('completion_reason', 'Unknown reason')}"
            ))
            
            conn.commit()
        
        logger.info("🏁 Trade completion logged", trade_id=trade_id, duration_minutes=duration_minutes)
    
    def get_all_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all trades with details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM trades 
                ORDER BY initiated_at DESC 
                LIMIT ?
            """, (limit,))
            
            trades = []
            for row in cursor.fetchall():
                trade = dict(row)
                trade["coins"] = json.loads(trade["coins"]) if trade["coins"] else []
                trades.append(trade)
            
            return trades
    
    def get_trade_timeline(self, trade_id: str) -> List[Dict[str, Any]]:
        """Get detailed timeline for a specific trade."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM trade_updates 
                WHERE trade_id = ? 
                ORDER BY timestamp ASC
            """, (trade_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trade_stats(self) -> Dict[str, Any]:
        """Get trading statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    COUNT(CASE WHEN status = 'active' THEN 1 END) as active_trades,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_trades,
                    AVG(duration_minutes) as avg_duration_minutes,
                    AVG(monitoring_cycles) as avg_monitoring_cycles
                FROM trades
            """)
            
            row = cursor.fetchone()
            return {
                "total_trades": row[0] or 0,
                "active_trades": row[1] or 0,
                "completed_trades": row[2] or 0,
                "avg_duration_minutes": round(row[3] or 0, 1),
                "avg_monitoring_cycles": round(row[4] or 0, 1)
            }


class TradeDashboard:
    """Flask web dashboard for trade auditing."""
    
    def __init__(self, auditor: TradeAuditor, port: int = 5000):
        self.auditor = auditor
        self.port = port
        self.app = Flask(__name__, template_folder="templates")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route("/")
        def dashboard():
            """Main dashboard page."""
            return render_template("dashboard.html")
        
        @self.app.route("/api/trades")
        def api_trades():
            """API endpoint for trades data."""
            limit = request.args.get("limit", 50, type=int)
            trades = self.auditor.get_all_trades(limit)
            return jsonify(trades)
        
        @self.app.route("/api/trade/<trade_id>/timeline")
        def api_trade_timeline(trade_id):
            """API endpoint for trade timeline."""
            timeline = self.auditor.get_trade_timeline(trade_id)
            return jsonify(timeline)
        
        @self.app.route("/api/stats")
        def api_stats():
            """API endpoint for trading statistics."""
            stats = self.auditor.get_trade_stats()
            return jsonify(stats)
    
    def run(self, debug: bool = False):
        """Run the Flask dashboard."""
        logger.info("🌐 Starting trade dashboard", port=self.port)
        self.app.run(host="0.0.0.0", port=self.port, debug=debug)
    
    def run_in_background(self):
        """Run the dashboard in a background thread."""
        def run_server():
            self.app.run(host="0.0.0.0", port=self.port, debug=False)
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        logger.info("🌐 Trade dashboard started in background", port=self.port, url=f"http://localhost:{self.port}")
        return thread


def create_dashboard(db_path: str = "data/trades.db", port: int = 5000) -> TradeDashboard:
    """Create and return a trade dashboard instance."""
    auditor = TradeAuditor(db_path)
    dashboard = TradeDashboard(auditor, port)
    return dashboard


if __name__ == "__main__":
    # Run dashboard standalone
    dashboard = create_dashboard()
    dashboard.run(debug=True)
