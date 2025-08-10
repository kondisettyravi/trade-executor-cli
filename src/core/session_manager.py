"""Session management for trading sessions and trade history."""

import sqlite3
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import structlog
from pathlib import Path

from .config import DatabaseConfig

logger = structlog.get_logger(__name__)


class SessionManager:
    """Manages trading sessions and trade history in SQLite database."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.db_path = config.path
        self._ensure_database_exists()
        self._initialize_tables()
    
    def _ensure_database_exists(self):
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _initialize_tables(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        ended_at TEXT,
                        status TEXT NOT NULL DEFAULT 'active',
                        emergency_stop BOOLEAN DEFAULT FALSE,
                        total_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        metadata TEXT
                    )
                """)
                
                # Trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        entry_price REAL,
                        exit_price REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        order_id TEXT,
                        order_link_id TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        closed_at TEXT,
                        pnl REAL DEFAULT 0.0,
                        decision_reasoning TEXT,
                        confidence REAL,
                        emergency_close BOOLEAN DEFAULT FALSE,
                        metadata TEXT,
                        FOREIGN KEY (session_id) REFERENCES sessions (id)
                    )
                """)
                
                # Performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        win_rate REAL DEFAULT 0.0,
                        avg_win REAL DEFAULT 0.0,
                        avg_loss REAL DEFAULT 0.0,
                        max_drawdown REAL DEFAULT 0.0,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Risk events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS risk_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        trade_id TEXT,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        description TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        metadata TEXT
                    )
                """)
                
                conn.commit()
                logger.info("Database tables initialized successfully")
                
        except Exception as e:
            logger.error("Failed to initialize database tables", error=str(e))
            raise
    
    async def create_session(self) -> Dict[str, Any]:
        """Create a new trading session."""
        try:
            session_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sessions (id, created_at, status)
                    VALUES (?, ?, 'active')
                """, (session_id, created_at))
                conn.commit()
            
            session = {
                "id": session_id,
                "created_at": created_at,
                "status": "active",
                "total_trades": 0,
                "total_pnl": 0.0
            }
            
            logger.info("New trading session created", session_id=session_id)
            return session
            
        except Exception as e:
            logger.error("Failed to create session", error=str(e))
            raise
    
    async def end_session(self, session_id: str, emergency: bool = False) -> Dict[str, Any]:
        """End a trading session."""
        try:
            ended_at = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update session
                cursor.execute("""
                    UPDATE sessions 
                    SET ended_at = ?, status = 'ended', emergency_stop = ?
                    WHERE id = ?
                """, (ended_at, emergency, session_id))
                
                # Get session statistics
                cursor.execute("""
                    SELECT COUNT(*) as total_trades, COALESCE(SUM(pnl), 0) as total_pnl
                    FROM trades 
                    WHERE session_id = ?
                """, (session_id,))
                
                stats = cursor.fetchone()
                total_trades, total_pnl = stats if stats else (0, 0.0)
                
                # Update session with final stats
                cursor.execute("""
                    UPDATE sessions 
                    SET total_trades = ?, total_pnl = ?
                    WHERE id = ?
                """, (total_trades, total_pnl, session_id))
                
                conn.commit()
            
            logger.info(
                "Trading session ended",
                session_id=session_id,
                emergency=emergency,
                total_trades=total_trades,
                total_pnl=total_pnl
            )
            
            return {
                "session_id": session_id,
                "ended_at": ended_at,
                "total_trades": total_trades,
                "total_pnl": total_pnl,
                "emergency": emergency
            }
            
        except Exception as e:
            logger.error("Failed to end session", session_id=session_id, error=str(e))
            raise
    
    async def save_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Save a trade to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades (
                        id, session_id, symbol, side, quantity, entry_price,
                        stop_loss, take_profit, order_id, order_link_id,
                        status, created_at, decision_reasoning, confidence,
                        metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade["id"],
                    trade["session_id"],
                    trade["symbol"],
                    trade["side"],
                    trade["quantity"],
                    trade.get("entry_price"),
                    trade.get("stop_loss"),
                    trade.get("take_profit"),
                    trade.get("order_id"),
                    trade.get("order_link_id"),
                    trade["status"],
                    trade["created_at"],
                    trade.get("decision_reasoning"),
                    trade.get("confidence"),
                    json.dumps(trade.get("metadata", {}))
                ))
                conn.commit()
            
            logger.info("Trade saved to database", trade_id=trade["id"])
            return trade
            
        except Exception as e:
            logger.error("Failed to save trade", trade_id=trade.get("id"), error=str(e))
            raise
    
    async def update_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing trade in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE trades SET
                        exit_price = ?,
                        stop_loss = ?,
                        take_profit = ?,
                        status = ?,
                        closed_at = ?,
                        pnl = ?,
                        emergency_close = ?,
                        metadata = ?
                    WHERE id = ?
                """, (
                    trade.get("exit_price"),
                    trade.get("stop_loss"),
                    trade.get("take_profit"),
                    trade["status"],
                    trade.get("closed_at"),
                    trade.get("pnl", 0.0),
                    trade.get("emergency_close", False),
                    json.dumps(trade.get("metadata", {})),
                    trade["id"]
                ))
                conn.commit()
            
            logger.info("Trade updated in database", trade_id=trade["id"])
            return trade
            
        except Exception as e:
            logger.error("Failed to update trade", trade_id=trade.get("id"), error=str(e))
            raise
    
    async def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get session history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM sessions 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                columns = [description[0] for description in cursor.description]
                sessions = []
                
                for row in cursor.fetchall():
                    session = dict(zip(columns, row))
                    sessions.append(session)
                
                return sessions
                
        except Exception as e:
            logger.error("Failed to get session history", error=str(e))
            return []
    
    async def get_trade_history(
        self, 
        session_id: Optional[str] = None, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get trade history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if session_id:
                    cursor.execute("""
                        SELECT * FROM trades 
                        WHERE session_id = ?
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (session_id, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM trades 
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (limit,))
                
                columns = [description[0] for description in cursor.description]
                trades = []
                
                for row in cursor.fetchall():
                    trade = dict(zip(columns, row))
                    # Parse metadata JSON
                    if trade.get("metadata"):
                        try:
                            trade["metadata"] = json.loads(trade["metadata"])
                        except json.JSONDecodeError:
                            trade["metadata"] = {}
                    trades.append(trade)
                
                return trades
                
        except Exception as e:
            logger.error("Failed to get trade history", error=str(e))
            return []
    
    async def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, Any]:
        """Get daily trading statistics."""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
                        COALESCE(SUM(pnl), 0) as total_pnl,
                        COALESCE(AVG(CASE WHEN pnl > 0 THEN pnl END), 0) as avg_win,
                        COALESCE(AVG(CASE WHEN pnl < 0 THEN pnl END), 0) as avg_loss
                    FROM trades 
                    WHERE DATE(created_at) = ?
                """, (date,))
                
                row = cursor.fetchone()
                if row:
                    total_trades, winning_trades, losing_trades, total_pnl, avg_win, avg_loss = row
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    
                    return {
                        "date": date,
                        "total_trades": total_trades,
                        "winning_trades": winning_trades,
                        "losing_trades": losing_trades,
                        "total_pnl": total_pnl,
                        "win_rate": win_rate,
                        "avg_win": avg_win,
                        "avg_loss": avg_loss
                    }
                else:
                    return {
                        "date": date,
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "total_pnl": 0.0,
                        "win_rate": 0.0,
                        "avg_win": 0.0,
                        "avg_loss": 0.0
                    }
                    
        except Exception as e:
            logger.error("Failed to get daily stats", date=date, error=str(e))
            return {}
    
    async def log_risk_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        session_id: Optional[str] = None,
        trade_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a risk management event."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO risk_events (
                        session_id, trade_id, event_type, severity,
                        description, created_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    trade_id,
                    event_type,
                    severity,
                    description,
                    datetime.now().isoformat(),
                    json.dumps(metadata or {})
                ))
                conn.commit()
            
            logger.info(
                "Risk event logged",
                event_type=event_type,
                severity=severity,
                session_id=session_id
            )
            
        except Exception as e:
            logger.error("Failed to log risk event", error=str(e))
    
    async def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get performance summary for the last N days."""
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades,
                        COALESCE(SUM(pnl), 0) as total_pnl,
                        COALESCE(MAX(pnl), 0) as best_trade,
                        COALESCE(MIN(pnl), 0) as worst_trade,
                        COALESCE(AVG(pnl), 0) as avg_pnl
                    FROM trades 
                    WHERE DATE(created_at) >= ?
                    AND status = 'closed'
                """, (start_date,))
                
                row = cursor.fetchone()
                if row:
                    (total_trades, winning_trades, losing_trades, 
                     total_pnl, best_trade, worst_trade, avg_pnl) = row
                    
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    
                    return {
                        "period_days": days,
                        "total_trades": total_trades,
                        "winning_trades": winning_trades,
                        "losing_trades": losing_trades,
                        "win_rate": win_rate,
                        "total_pnl": total_pnl,
                        "avg_pnl": avg_pnl,
                        "best_trade": best_trade,
                        "worst_trade": worst_trade
                    }
                else:
                    return {
                        "period_days": days,
                        "total_trades": 0,
                        "winning_trades": 0,
                        "losing_trades": 0,
                        "win_rate": 0.0,
                        "total_pnl": 0.0,
                        "avg_pnl": 0.0,
                        "best_trade": 0.0,
                        "worst_trade": 0.0
                    }
                    
        except Exception as e:
            logger.error("Failed to get performance summary", error=str(e))
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data beyond the retention period."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old trades
                cursor.execute("""
                    DELETE FROM trades 
                    WHERE DATE(created_at) < ?
                """, (cutoff_date,))
                
                # Delete old sessions
                cursor.execute("""
                    DELETE FROM sessions 
                    WHERE DATE(created_at) < ?
                """, (cutoff_date,))
                
                # Delete old risk events
                cursor.execute("""
                    DELETE FROM risk_events 
                    WHERE DATE(created_at) < ?
                """, (cutoff_date,))
                
                conn.commit()
                
                logger.info("Old data cleaned up", cutoff_date=cutoff_date)
                
        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
