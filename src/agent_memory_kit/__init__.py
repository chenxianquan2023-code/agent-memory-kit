"""
Agent Memory Kit - Production-ready memory framework for AI agents.
"""

__version__ = "0.2.0"

from .memory_manager import MemoryManager, MemoryConfig
from .compressor import Compressor, CompressionConfig
from .validator import ReplayValidator, ValidationResult
from .vector_store import VectorMemory, VectorEntry
from .graph_store import MemoryGraph, Entity, Relation

try:
    from .web.dashboard import MemoryDashboard, launch_dashboard
    HAS_DASHBOARD = True
except ImportError:
    HAS_DASHBOARD = False

__all__ = [
    "MemoryManager",
    "MemoryConfig",
    "Compressor",
    "CompressionConfig",
    "ReplayValidator",
    "ValidationResult",
    "VectorMemory",
    "VectorEntry",
    "MemoryGraph",
    "Entity",
    "Relation",
]

if HAS_DASHBOARD:
    __all__.extend(["MemoryDashboard", "launch_dashboard"])
