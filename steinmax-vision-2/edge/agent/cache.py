"""
Plate Cache - Redis + SQLite Fallback

Uses Redis for fast lookups, with SQLite as fallback when Redis is unavailable.
"""

import json
import logging
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)


class PlateCache:
    """
    Fast plate lookup cache using Redis.
    
    Falls back to SQLite if Redis is unavailable.
    """
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._sqlite_path = settings.sqlite_path
        self._connected = False
    
    async def connect(self):
        """Initialize connections."""
        # Connect to Redis
        try:
            self._redis = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis unavailable, using SQLite fallback: {e}")
            self._redis = None
        
        # Initialize SQLite fallback
        await self._init_sqlite()
    
    async def close(self):
        """Close connections."""
        if self._redis:
            await self._redis.close()
    
    async def _init_sqlite(self):
        """Initialize SQLite fallback database."""
        Path(self._sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self._sqlite_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS plates (
                    plate_number TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)
            await db.commit()
        
        logger.info(f"SQLite fallback initialized at {self._sqlite_path}")
    
    async def check_plate(self, plate_number: str) -> dict:
        """
        Check if a plate is allowed.
        
        Returns:
            {
                "allowed": bool,
                "plate_id": str | None,
                "description": str | None,
                "list_type": str | None,
                "reason": str
            }
        """
        normalized = plate_number.upper().replace(" ", "").replace("-", "")
        
        # Try Redis first
        if self._redis:
            try:
                data = await self._redis.get(f"plate:{normalized}")
                if data:
                    return self._evaluate_plate(json.loads(data), normalized)
            except Exception as e:
                logger.warning(f"Redis error, falling back to SQLite: {e}")
        
        # Fall back to SQLite
        return await self._check_plate_sqlite(normalized)
    
    async def _check_plate_sqlite(self, plate_number: str) -> dict:
        """Check plate in SQLite."""
        async with aiosqlite.connect(self._sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT data FROM plates WHERE plate_number = ?",
                (plate_number,)
            ) as cursor:
                row = await cursor.fetchone()
        
        if row:
            return self._evaluate_plate(json.loads(row["data"]), plate_number)
        
        return {
            "allowed": False,
            "plate_id": None,
            "description": None,
            "list_type": None,
            "reason": "Plate not found in allow list",
        }
    
    def _evaluate_plate(self, plate_data: dict, plate_number: str) -> dict:
        """Evaluate plate rules (expiry, time windows, etc.)."""
        now = datetime.now(timezone.utc)
        
        # Check deny list
        if plate_data.get("list_type") == "deny":
            return {
                "allowed": False,
                "plate_id": plate_data.get("id"),
                "description": plate_data.get("description"),
                "list_type": "deny",
                "reason": "Plate is on deny list",
            }
        
        # Check expiration
        expires_at = plate_data.get("expires_at")
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp_dt < now:
                    return {
                        "allowed": False,
                        "plate_id": plate_data.get("id"),
                        "description": plate_data.get("description"),
                        "list_type": plate_data.get("list_type"),
                        "reason": "Plate authorization has expired",
                    }
            except Exception as e:
                logger.warning(f"Error parsing expiry date: {e}")
        
        # Check start time
        starts_at = plate_data.get("starts_at")
        if starts_at:
            try:
                start_dt = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
                if start_dt > now:
                    return {
                        "allowed": False,
                        "plate_id": plate_data.get("id"),
                        "description": plate_data.get("description"),
                        "list_type": plate_data.get("list_type"),
                        "reason": "Plate authorization not yet active",
                    }
            except Exception as e:
                logger.warning(f"Error parsing start date: {e}")
        
        # TODO: Check schedule (time-of-day restrictions)
        # schedule = plate_data.get("schedule")
        # if schedule:
        #     if not self._is_within_schedule(schedule, now):
        #         return {...}
        
        # Plate is allowed
        return {
            "allowed": True,
            "plate_id": plate_data.get("id"),
            "description": plate_data.get("description"),
            "list_type": plate_data.get("list_type", "allow"),
            "reason": "Plate matched allow list",
        }
    
    async def sync_plates(self, plates: list[dict]) -> int:
        """
        Sync plates from cloud.
        
        Updates both Redis and SQLite.
        """
        count = 0
        
        # Update Redis
        if self._redis:
            try:
                pipe = self._redis.pipeline()
                
                # Clear existing plates
                keys = await self._redis.keys("plate:*")
                if keys:
                    await self._redis.delete(*keys)
                
                # Add new plates
                for plate in plates:
                    plate_number = plate.get("plate_number", "").upper().replace(" ", "")
                    if plate_number:
                        pipe.set(
                            f"plate:{plate_number}",
                            json.dumps(plate),
                            ex=settings.redis_plate_ttl,
                        )
                        count += 1
                
                await pipe.execute()
                logger.info(f"Synced {count} plates to Redis")
            except Exception as e:
                logger.error(f"Redis sync error: {e}")
        
        # Update SQLite (always, as fallback)
        await self._sync_plates_sqlite(plates)
        
        return count
    
    async def _sync_plates_sqlite(self, plates: list[dict]):
        """Sync plates to SQLite."""
        async with aiosqlite.connect(self._sqlite_path) as db:
            await db.execute("DELETE FROM plates")
            
            for plate in plates:
                plate_number = plate.get("plate_number", "").upper().replace(" ", "")
                if plate_number:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO plates (plate_number, data, updated_at)
                        VALUES (?, ?, ?)
                        """,
                        (plate_number, json.dumps(plate), datetime.now(timezone.utc).isoformat())
                    )
            
            await db.execute(
                """
                INSERT OR REPLACE INTO sync_meta (key, value)
                VALUES ('last_sync', ?)
                """,
                (datetime.now(timezone.utc).isoformat(),)
            )
            
            await db.commit()
        
        logger.info(f"Synced {len(plates)} plates to SQLite")
    
    async def get_plate_count(self) -> int:
        """Get number of cached plates."""
        if self._redis:
            try:
                keys = await self._redis.keys("plate:*")
                return len(keys)
            except Exception:
                pass
        
        async with aiosqlite.connect(self._sqlite_path) as db:
            async with db.execute("SELECT COUNT(*) FROM plates") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    
    async def get_last_sync(self) -> Optional[str]:
        """Get timestamp of last sync."""
        async with aiosqlite.connect(self._sqlite_path) as db:
            async with db.execute(
                "SELECT value FROM sync_meta WHERE key = 'last_sync'"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
