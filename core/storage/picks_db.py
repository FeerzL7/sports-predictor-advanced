# core/storage/picks_db.py

"""
Sistema de persistencia para picks y resultados.

Características:
- SQLite para simplicidad (sin servidor)
- Schema normalizado (picks, events, results)
- CRUD completo
- Queries de análisis (ROI, win rate, etc)
- Thread-safe
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

from core.utils.logger import setup_logger

logger = setup_logger(__name__)


# =========================
# CONFIGURACIÓN
# =========================

DB_DIR = Path("data")
DB_DIR.mkdir(exist_ok=True)

DEFAULT_DB_PATH = DB_DIR / "picks.db"


# =========================
# DATABASE CLASS
# =========================

class PicksDatabase:
    """
    Gestión de picks, eventos y resultados.
    
    Uso:
        db = PicksDatabase()
        db.save_pick(pick_dict)
        pending = db.get_pending_picks()
        db.update_result(pick_id, "WIN", 15.50)
    """
    
    def __init__(self, db_path: str = None):
        """
        Args:
            db_path: Path al archivo SQLite (default: data/picks.db)
        """
        self.db_path = db_path or str(DEFAULT_DB_PATH)
        self._init_schema()
        logger.info(f"PicksDatabase initialized: {self.db_path}")
    
    # =========================
    # CONTEXT MANAGER (THREAD-SAFE)
    # =========================
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones thread-safe."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    # =========================
    # SCHEMA
    # =========================
    
    def _init_schema(self):
        """Crea tablas si no existen."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla: events (partidos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    sport TEXT NOT NULL,
                    league TEXT NOT NULL,
                    date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    venue TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: picks
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    market TEXT NOT NULL,
                    side TEXT NOT NULL,
                    team TEXT,
                    line REAL,
                    odds REAL NOT NULL,
                    odds_format TEXT DEFAULT 'decimal',
                    model_prob REAL NOT NULL,
                    implied_prob REAL NOT NULL,
                    edge REAL NOT NULL,
                    confidence REAL NOT NULL,
                    stake_pct REAL,
                    stake_amount REAL,
                    reason TEXT,
                    correlation_reason TEXT,
                    result TEXT DEFAULT 'PENDING',
                    actual_outcome TEXT,
                    profit REAL,
                    roi REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT,
                    FOREIGN KEY (event_id) REFERENCES events(event_id)
                )
            """)
            
            # Tabla: performance_summary (para caching de stats)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    sport TEXT,
                    league TEXT,
                    market TEXT,
                    total_picks INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    pushes INTEGER DEFAULT 0,
                    pending INTEGER DEFAULT 0,
                    total_stake REAL DEFAULT 0.0,
                    total_profit REAL DEFAULT 0.0,
                    roi REAL DEFAULT 0.0,
                    avg_edge REAL DEFAULT 0.0,
                    avg_confidence REAL DEFAULT 0.0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(period, sport, league, market)
                )
            """)
            
            # Índices para performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_picks_result 
                ON picks(result)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_picks_event 
                ON picks(event_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_picks_created 
                ON picks(created_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_date 
                ON events(date)
            """)
            
            logger.info("Database schema initialized")
    
    # =========================
    # CREATE
    # =========================
    
    def save_event(
        self,
        event_id: str,
        sport: str,
        league: str,
        date: str,
        home_team: str,
        away_team: str,
        venue: str = None
    ) -> int:
        """
        Guarda un evento (partido).
        
        Returns:
            ID del evento insertado (o existente)
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO events (event_id, sport, league, date, home_team, away_team, venue)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (event_id, sport, league, date, home_team, away_team, venue))
                
                event_pk = cursor.lastrowid
                logger.debug(f"Event saved: {event_id}")
                
            except sqlite3.IntegrityError:
                # Ya existe, obtener ID
                cursor.execute("SELECT id FROM events WHERE event_id = ?", (event_id,))
                event_pk = cursor.fetchone()[0]
                logger.debug(f"Event already exists: {event_id}")
            
            return event_pk
    
    def save_pick(self, pick: Dict[str, Any]) -> int:
        """
        Guarda un pick.
        
        Args:
            pick: Dict con keys: event_id, market, side, team, odds, 
                  model_prob, edge, confidence, etc.
        
        Returns:
            ID del pick insertado
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO picks (
                    event_id, market, side, team, line, odds, odds_format,
                    model_prob, implied_prob, edge, confidence,
                    stake_pct, stake_amount, reason, correlation_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pick.get("event_id"),
                pick.get("market"),
                pick.get("side"),
                pick.get("team"),
                pick.get("line"),
                pick.get("odds"),
                pick.get("odds_format", "decimal"),
                pick.get("model_prob"),
                pick.get("implied_prob"),
                pick.get("edge"),
                pick.get("confidence"),
                pick.get("stake_pct"),
                pick.get("stake"),
                pick.get("reason"),
                pick.get("correlation_reason")
            ))
            
            pick_id = cursor.lastrowid
            
            logger.info(
                f"Pick saved (ID={pick_id}): {pick.get('market')} | "
                f"{pick.get('team')} {pick.get('side')} | "
                f"Edge={pick.get('edge', 0)*100:.1f}%"
            )
            
            return pick_id
    
    # =========================
    # READ
    # =========================
    
    def get_pick(self, pick_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene un pick por ID."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM picks WHERE id = ?", (pick_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_pending_picks(self) -> List[Dict[str, Any]]:
        """Obtiene todos los picks pendientes de resultado."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.*, e.home_team, e.away_team, e.date
                FROM picks p
                JOIN events e ON p.event_id = e.event_id
                WHERE p.result = 'PENDING'
                ORDER BY e.date DESC, p.created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_picks_by_date(self, date: str) -> List[Dict[str, Any]]:
        """Obtiene picks de una fecha específica."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.*, e.home_team, e.away_team
                FROM picks p
                JOIN events e ON p.event_id = e.event_id
                WHERE e.date = ?
                ORDER BY p.created_at DESC
            """, (date,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_picks_by_event(self, event_id: str) -> List[Dict[str, Any]]:
        """Obtiene todos los picks de un evento."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM picks 
                WHERE event_id = ?
                ORDER BY created_at
            """, (event_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_picks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Últimos N picks."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT p.*, e.home_team, e.away_team, e.date
                FROM picks p
                JOIN events e ON p.event_id = e.event_id
                ORDER BY p.created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # =========================
    # UPDATE
    # =========================
    
    def update_result(
        self,
        pick_id: int,
        result: str,
        actual_outcome: str = None,
        profit: float = None
    ) -> bool:
        """
        Actualiza el resultado de un pick.
        
        Args:
            pick_id: ID del pick
            result: "WIN", "LOSS", "PUSH"
            actual_outcome: Resultado real (ej: "5-3")
            profit: Ganancia/pérdida en unidades
        
        Returns:
            True si se actualizó correctamente
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Calcular ROI si hay profit y stake
            roi = None
            if profit is not None:
                cursor.execute("SELECT stake_amount FROM picks WHERE id = ?", (pick_id,))
                row = cursor.fetchone()
                if row and row[0]:
                    stake = row[0]
                    roi = (profit / stake) if stake > 0 else 0.0
            
            cursor.execute("""
                UPDATE picks
                SET result = ?,
                    actual_outcome = ?,
                    profit = ?,
                    roi = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (result, actual_outcome, profit, roi, pick_id))
            
            if cursor.rowcount > 0:
                logger.info(f"Pick {pick_id} updated: {result} | Profit={profit}")
                return True
            
            logger.warning(f"Pick {pick_id} not found")
            return False
    
    # =========================
    # DELETE
    # =========================
    
    def delete_pick(self, pick_id: int) -> bool:
        """Elimina un pick (usar con cuidado)."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM picks WHERE id = ?", (pick_id,))
            
            if cursor.rowcount > 0:
                logger.warning(f"Pick {pick_id} deleted")
                return True
            
            return False
    
    # =========================
    # ANALYTICS
    # =========================
    
    def get_performance_stats(
        self,
        sport: str = None,
        league: str = None,
        market: str = None,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """
        Calcula estadísticas de performance.
        
        Returns:
            Dict con: total_picks, wins, losses, pushes, win_rate,
                     total_profit, roi, avg_edge, avg_confidence, etc.
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Construir query dinámicamente
            query = """
                SELECT 
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN result = 'PUSH' THEN 1 ELSE 0 END) as pushes,
                    SUM(CASE WHEN result = 'PENDING' THEN 1 ELSE 0 END) as pending,
                    SUM(stake_amount) as total_stake,
                    SUM(profit) as total_profit,
                    AVG(edge) as avg_edge,
                    AVG(confidence) as avg_confidence,
                    AVG(odds) as avg_odds
                FROM picks p
                JOIN events e ON p.event_id = e.event_id
                WHERE 1=1
            """
            
            params = []
            
            if sport:
                query += " AND e.sport = ?"
                params.append(sport)
            
            if league:
                query += " AND e.league = ?"
                params.append(league)
            
            if market:
                query += " AND p.market = ?"
                params.append(market)
            
            if start_date:
                query += " AND e.date >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND e.date <= ?"
                params.append(end_date)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            # Manejar caso cuando no hay datos
            if not row:
                return {
                    "total_picks": 0,
                    "wins": 0,
                    "losses": 0,
                    "pushes": 0,
                    "pending": 0,
                    "total_stake": 0.0,
                    "total_profit": 0.0,
                    "win_rate": 0.0,
                    "roi": 0.0,
                    "avg_edge": 0.0,
                    "avg_confidence": 0.0,
                    "avg_odds": 0.0
                }
            
            stats = dict(row)
            
            # Convertir None a 0 para valores numéricos
            for key in ["total_picks", "wins", "losses", "pushes", "pending"]:
                if stats.get(key) is None:
                    stats[key] = 0
            
            for key in ["total_stake", "total_profit", "avg_edge", "avg_confidence", "avg_odds"]:
                if stats.get(key) is None:
                    stats[key] = 0.0
            
            # Calcular métricas derivadas
            total = stats["total_picks"]
            wins = stats["wins"]
            losses = stats["losses"]
            decided = wins + losses
            
            stats["win_rate"] = (wins / decided) if decided > 0 else 0.0
            stats["roi"] = (
                (stats["total_profit"] / stats["total_stake"])
                if stats["total_stake"] and stats["total_stake"] > 0
                else 0.0
            )
            
            # Redondear
            for key in ["avg_edge", "avg_confidence", "avg_odds", "win_rate", "roi"]:
                if stats.get(key) is not None:
                    stats[key] = round(stats[key], 4)
            
            return stats
    
    def get_performance_by_market(self) -> List[Dict[str, Any]]:
        """Performance desglosada por mercado."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    market,
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(profit) as total_profit,
                    SUM(stake_amount) as total_stake,
                    AVG(edge) as avg_edge,
                    AVG(confidence) as avg_confidence
                FROM picks
                WHERE result != 'PENDING'
                GROUP BY market
                ORDER BY total_picks DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                data = dict(row)
                
                # Manejar None values
                wins = data.get("wins") or 0
                losses = data.get("losses") or 0
                total_profit = data.get("total_profit") or 0.0
                total_stake = data.get("total_stake") or 0.0
                
                decided = wins + losses
                data["win_rate"] = (wins / decided) if decided > 0 else 0.0
                data["roi"] = (total_profit / total_stake) if total_stake > 0 else 0.0
                
                results.append(data)
            
            return results
    
    # =========================
    # UTILITIES
    # =========================
    
    def count_picks(self, result: str = None) -> int:
        """Cuenta picks por resultado."""
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if result:
                cursor.execute(
                    "SELECT COUNT(*) FROM picks WHERE result = ?",
                    (result,)
                )
            else:
                cursor.execute("SELECT COUNT(*) FROM picks")
            
            return cursor.fetchone()[0]
    
    def clear_all_picks(self) -> int:
        """
        PELIGRO: Elimina TODOS los picks.
        Usar solo en testing.
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM picks")
            deleted = cursor.rowcount
            
            logger.warning(f"ALL PICKS DELETED: {deleted} rows")
            
            return deleted
    
    def export_to_json(self, filepath: str):
        """Exporta picks a JSON."""
        
        picks = self.get_recent_picks(limit=10000)  # Todos
        
        with open(filepath, 'w') as f:
            json.dump(picks, f, indent=2, default=str)
        
        logger.info(f"Picks exported to {filepath}")