"""
Memory compression strategies.
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CompressionConfig:
    """Configuration for compression strategies."""
    strategy: str = "semantic"  # semantic | summarization | extraction
    preserve_fields: Optional[List[str]] = None
    max_summary_length: int = 500


class Compressor:
    """
    Compress memory entries to save space while preserving value.
    
    Strategies:
    - semantic: Keep key concepts, remove fluff
    - summarization: Create concise summary
    - extraction: Extract only specific fields
    """
    
    def __init__(self, config: Optional[CompressionConfig] = None):
        self.config = config or CompressionConfig()
    
    def compress(self, data: Any) -> Any:
        """
        Compress data based on configured strategy.
        """
        if self.config.strategy == "extraction":
            return self._extract_strategy(data)
        elif self.config.strategy == "summarization":
            return self._summarize_strategy(data)
        elif self.config.strategy == "semantic":
            return self._semantic_strategy(data)
        else:
            return data  # No compression
    
    def _extract_strategy(self, data: Any) -> Any:
        """Extract only specified fields."""
        if not isinstance(data, dict):
            return data
        
        if not self.config.preserve_fields:
            return data
        
        return {
            k: v for k, v in data.items()
            if k in self.config.preserve_fields
        }
    
    def _summarize_strategy(self, data: Any) -> Any:
        """
        Create a summary of the data.
        
        For text: truncate with ellipsis
        For lists: keep first N items
        For dicts: keep key fields
        """
        if isinstance(data, str):
            if len(data) > self.config.max_summary_length:
                return data[:self.config.max_summary_length] + "... [truncated]"
            return data
        
        elif isinstance(data, list):
            # Keep first 5 items, note if more
            if len(data) > 5:
                return {
                    "items": data[:5],
                    "note": f"... and {len(data) - 5} more items",
                    "total": len(data)
                }
            return data
        
        elif isinstance(data, dict):
            # Create summary of dict
            summary = {"_summary": True}
            
            # Always keep these if present
            key_fields = ["decision", "outcome", "learning", "error"]
            for field in key_fields:
                if field in data:
                    summary[field] = data[field]
            
            # Add count of other fields
            other_fields = [k for k in data.keys() if k not in key_fields]
            if other_fields:
                summary["_other_fields"] = len(other_fields)
            
            return summary
        
        return data
    
    def _semantic_strategy(self, data: Any) -> Any:
        """
        Keep semantically important parts.
        
        For conversations: keep decisions, learnings, not chatter
        For logs: keep errors and warnings, not info
        For configs: keep all (usually small)
        """
        if isinstance(data, str):
            # For text, try to extract key sentences
            return self._extract_key_sentences(data)
        
        elif isinstance(data, list) and len(data) > 0:
            # Filter list items
            filtered = []
            for item in data:
                if self._is_semantically_important(item):
                    filtered.append(item)
            
            if len(filtered) < len(data):
                return {
                    "important_items": filtered,
                    "filtered_count": len(data) - len(filtered),
                    "total": len(data)
                }
            return data
        
        elif isinstance(data, dict):
            # Keep only important keys
            important_keys = [
                "decision", "error", "learning", "outcome",
                "config", "preference", "setting"
            ]
            
            compressed = {}
            for key in important_keys:
                if key in data:
                    compressed[key] = data[key]
            
            # Note if we filtered
            if len(compressed) < len(data):
                compressed["_filtered_keys"] = len(data) - len(compressed)
            
            return compressed if compressed else data
        
        return data
    
    def _extract_key_sentences(self, text: str) -> str:
        """Extract sentences that contain key information."""
        sentences = text.split('. ')
        
        key_indicators = [
            "decided", "chose", "selected", "opted",
            "error", "failed", "bug", "issue",
            "learned", "realized", "understood",
            "config", "setting", "changed"
        ]
        
        key_sentences = [
            s for s in sentences
            if any(ind in s.lower() for ind in key_indicators)
        ]
        
        if key_sentences:
            return '. '.join(key_sentences[:3]) + '.'
        
        # Fallback: return first sentence
        return sentences[0] + '.' if sentences else text[:200]
    
    def _is_semantically_important(self, item: Any) -> bool:
        """Check if an item is semantically important."""
        if isinstance(item, dict):
            # Important if it has certain keys
            important_keys = {"error", "decision", "learning", "outcome"}
            return bool(important_keys & set(item.keys()))
        
        if isinstance(item, str):
            # Check for key indicators
            indicators = ["error", "decided", "learned", "configured"]
            return any(ind in item.lower() for ind in indicators)
        
        return True  # Default: keep it
