"""
Core memory management with HOT/WARM/COLD layers.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class MemoryConfig:
    """Configuration for memory layers."""
    hot_max_lines: int = 200
    warm_max_lines: int = 500
    cold_compression_days: int = 7
    validation_sample_rate: float = 0.1


class MemoryManager:
    """
    Three-layer memory system for AI agents.
    
    HOT: Current session, always loaded
    WARM: Active preferences, loaded on demand
    COLD: Archived history, indexed retrieval
    """
    
    def __init__(self, workspace: str, config: Optional[MemoryConfig] = None):
        self.workspace = Path(workspace)
        self.config = config or MemoryConfig()
        
        # Create directory structure
        self.hot_dir = self.workspace / "memory" / "hot"
        self.warm_dir = self.workspace / "memory" / "warm"
        self.cold_dir = self.workspace / "memory" / "cold"
        
        for dir_path in [self.hot_dir, self.warm_dir, self.cold_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for HOT layer
        self._hot_cache: Dict[str, Any] = {}
        self._warm_cache: Dict[str, Any] = {}
        
        # Load HOT layer on init
        self._load_hot()
    
    def hot(self, key: str, value: Optional[Any] = None) -> Any:
        """
        Get or set HOT layer memory.
        HOT = Current session, always in memory.
        """
        if value is not None:
            self._hot_cache[key] = value
            self._persist_hot()
        return self._hot_cache.get(key)
    
    def warm(self, key: str, value: Optional[Any] = None) -> Any:
        """
        Get or set WARM layer memory.
        WARM = Active preferences, cached but persisted.
        """
        if value is not None:
            self._warm_cache[key] = value
            self._persist_warm()
            return value
        
        # Check cache first
        if key in self._warm_cache:
            return self._warm_cache[key]
        
        # Load from disk
        file_path = self.warm_dir / f"{key}.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                self._warm_cache[key] = data
                return data
        return None
    
    def cold(self, key: str, value: Optional[Any] = None) -> Any:
        """
        Get or set COLD layer memory.
        COLD = Archived history, loaded on demand.
        """
        file_path = self.cold_dir / f"{key}.json"
        
        if value is not None:
            with open(file_path, 'w') as f:
                json.dump(value, f, indent=2, default=str)
            return value
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def compress(self) -> Dict[str, int]:
        """
        Compress memory by moving old entries down the layers.
        Returns statistics of what was moved.
        """
        stats = {"hot_to_warm": 0, "warm_to_cold": 0}
        
        # HOT → WARM: Move non-essential hot entries
        if len(self._hot_cache) > self.config.hot_max_lines:
            excess = dict(list(self._hot_cache.items())[self.config.hot_max_lines:])
            for k, v in excess.items():
                self.warm(k, v)
                del self._hot_cache[k]
                stats["hot_to_warm"] += 1
        
        # WARM → COLD: Archive old warm entries
        warm_files = list(self.warm_dir.glob("*.json"))
        if len(warm_files) > self.config.warm_max_lines:
            # Sort by modification time
            warm_files.sort(key=lambda p: p.stat().st_mtime)
            excess_count = len(warm_files) - self.config.warm_max_lines
            for file_path in warm_files[:excess_count]:
                key = file_path.stem
                with open(file_path, 'r') as f:
                    data = json.load(f)
                # Archive to cold
                archive_key = f"{key}_{datetime.now().strftime('%Y%m%d')}"
                self.cold(archive_key, data)
                # Remove from warm
                file_path.unlink()
                if key in self._warm_cache:
                    del self._warm_cache[key]
                stats["warm_to_cold"] += 1
        
        return stats
    
    def _load_hot(self):
        """Load HOT layer from disk on init."""
        hot_file = self.hot_dir / "session.json"
        if hot_file.exists():
            with open(hot_file, 'r') as f:
                self._hot_cache = json.load(f)
    
    def _persist_hot(self):
        """Persist HOT layer to disk."""
        hot_file = self.hot_dir / "session.json"
        with open(hot_file, 'w') as f:
            json.dump(self._hot_cache, f, indent=2, default=str)
    
    def _persist_warm(self):
        """Persist WARM layer to disk."""
        for key, value in self._warm_cache.items():
            file_path = self.warm_dir / f"{key}.json"
            with open(file_path, 'w') as f:
                json.dump(value, f, indent=2, default=str)
    
    def get_stats(self) -> Dict[str, any]:
        """Get memory usage statistics."""
        return {
            "hot_entries": len(self._hot_cache),
            "warm_entries": len(list(self.warm_dir.glob("*.json"))),
            "cold_entries": len(list(self.cold_dir.glob("*.json"))),
            "workspace_size_mb": self._get_dir_size(self.workspace),
        }
    
    def _get_dir_size(self, path: Path) -> float:
        """Get directory size in MB."""
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return round(total / (1024 * 1024), 2)
