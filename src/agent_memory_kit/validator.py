"""
Replay validation to detect memory drift.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of memory validation."""
    total_checked: int
    accurate: int
    drifted: int
    missing: int
    accuracy: float
    details: List[Dict]


class ReplayValidator:
    """
    Validate memory accuracy by replaying past decisions.
    
    Based on Hazel_OC's research: without validation, 23% of "memories" are wrong.
    """
    
    def __init__(self, memory_manager):
        self.memory = memory_manager
        self.log_dir = memory_manager.workspace / "logs"
        self.log_dir.mkdir(exist_ok=True)
    
    def log_decision(self, context: str, decision: str, result: str, 
                     alternatives: Optional[List[str]] = None):
        """
        Log a decision for later validation.
        
        Args:
            context: What was the situation
            decision: What was decided
            result: What actually happened
            alternatives: Other options considered
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "decision": decision,
            "result": result,
            "alternatives": alternatives or [],
            "context_hash": self._hash_context(context)
        }
        
        # Append to daily log
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"decisions_{date_str}.jsonl"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def validate_replay(self, days: int = 7, sample_rate: float = 0.1) -> ValidationResult:
        """
        Validate memory by replaying past decisions.
        
        Args:
            days: How many days back to check
            sample_rate: Fraction of decisions to validate (0.1 = 10%)
            
        Returns:
            ValidationResult with accuracy stats
        """
        cutoff = datetime.now() - timedelta(days=days)
        decisions = self._load_decisions(cutoff)
        
        # Sample decisions to validate
        import random
        sample_size = max(1, int(len(decisions) * sample_rate))
        to_validate = random.sample(decisions, min(sample_size, len(decisions)))
        
        accurate = 0
        drifted = 0
        missing = 0
        details = []
        
        for decision in to_validate:
            # Check if memory still reflects this decision
            memory_value = self.memory.cold(f"decision_{decision['context_hash']}")
            
            if memory_value is None:
                missing += 1
                status = "missing"
            elif self._compare_decision(memory_value, decision):
                accurate += 1
                status = "accurate"
            else:
                drifted += 1
                status = "drifted"
            
            details.append({
                "timestamp": decision["timestamp"],
                "context": decision["context"][:100],  # Truncate for readability
                "status": status
            })
        
        total = len(to_validate)
        accuracy = (accurate / total * 100) if total > 0 else 0
        
        return ValidationResult(
            total_checked=total,
            accurate=accurate,
            drifted=drifted,
            missing=missing,
            accuracy=round(accuracy, 1),
            details=details
        )
    
    def _load_decisions(self, since: datetime) -> List[Dict]:
        """Load decision logs from files."""
        decisions = []
        
        for log_file in self.log_dir.glob("decisions_*.jsonl"):
            # Parse date from filename
            date_str = log_file.stem.replace("decisions_", "")
            try:
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date >= since:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                decisions.append(json.loads(line))
            except ValueError:
                continue
        
        return decisions
    
    def _hash_context(self, context: str) -> str:
        """Create a short hash of context for indexing."""
        return hash(context) % 10000  # Simple hash for demo
    
    def _compare_decision(self, memory_value: Dict, original: Dict) -> bool:
        """Check if memory matches original decision."""
        # Simple comparison - in production, use semantic similarity
        return memory_value.get("decision") == original.get("decision")
