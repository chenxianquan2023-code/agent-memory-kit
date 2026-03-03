# API Reference

Complete reference for Agent Memory Kit.

## MemoryManager

Main class for managing agent memory.

```python
from agent_memory_kit import MemoryManager

memory = MemoryManager(workspace="./my_workspace")
```

### Constructor

```python
MemoryManager(
    workspace: str,                    # Directory for memory files
    config: Optional[MemoryConfig]     # Configuration options
)
```

**Parameters:**
- `workspace`: Path to directory where memory files will be stored
- `config`: Optional configuration (see MemoryConfig below)

### Methods

#### `hot(key, value=None)`

Get or set HOT layer memory.

```python
# Set
memory.hot("current_task", "Building API")

# Get
task = memory.hot("current_task")
```

**Args:**
- `key`: String key for the memory
- `value`: Optional value to set. If None, returns current value.

**Returns:** Current value or None

**Layer:** HOT (session memory, always in RAM)

---

#### `warm(key, value=None)`

Get or set WARM layer memory.

```python
# Set
memory.warm("user_name", "Alice")

# Get (cached after first load)
name = memory.warm("user_name")
```

**Args:**
- `key`: String key for the memory
- `value`: Optional value to set. If None, returns current value.

**Returns:** Current value or None

**Layer:** WARM (working memory, cached, persisted)

---

#### `cold(key, value=None)`

Get or set COLD layer memory.

```python
# Archive old data
memory.cold("old_project_2024", project_data)

# Retrieve (slower)
old_data = memory.cold("old_project_2024")
```

**Args:**
- `key`: String key for the memory
- `value`: Optional value to set. If None, returns current value.

**Returns:** Current value or None

**Layer:** COLD (archive, compressed, on-demand)

---

#### `compress()`

Compress memory by moving entries down layers.

```python
stats = memory.compress()
print(f"Moved {stats['hot_to_warm']} from HOT to WARM")
print(f"Archived {stats['warm_to_cold']} from WARM to COLD")
```

**Returns:** Dict with compression statistics

---

#### `get_stats()`

Get memory usage statistics.

```python
stats = memory.get_stats()
print(stats)
# {
#     "hot_entries": 15,
#     "warm_entries": 127,
#     "cold_entries": 842,
#     "workspace_size_mb": 12.5
# }
```

**Returns:** Dict with memory statistics

---

## MemoryConfig

Configuration for memory manager.

```python
from agent_memory_kit import MemoryConfig

config = MemoryConfig(
    hot_max_lines=200,
    warm_max_lines=500,
    cold_compression_days=7,
    validation_sample_rate=0.1
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `hot_max_lines` | int | 200 | Maximum entries in HOT layer |
| `warm_max_lines` | int | 500 | Maximum entries in WARM layer |
| `cold_compression_days` | int | 7 | Days before compressing WARM → COLD |
| `validation_sample_rate` | float | 0.1 | Fraction of decisions to validate |

---

## ReplayValidator

Validate memory accuracy by replaying past decisions.

```python
from agent_memory_kit import MemoryManager, ReplayValidator

memory = MemoryManager("./workspace")
validator = ReplayValidator(memory)
```

### Methods

#### `log_decision(context, decision, result, alternatives=None)`

Log a decision for later validation.

```python
validator.log_decision(
    context="User asked to optimize API",
    decision="Added caching layer",
    result="Response time 200ms → 20ms",
    alternatives=["Add database index", "Use CDN", "Scale servers"]
)
```

**Args:**
- `context`: String describing the situation
- `decision`: String describing what was decided
- `result`: String describing the outcome
- `alternatives`: Optional list of other options considered

---

#### `validate_replay(days=7, sample_rate=0.1)`

Validate memory accuracy.

```python
results = validator.validate_replay(days=7, sample_rate=0.1)
print(f"Accuracy: {results.accuracy}%")
```

**Args:**
- `days`: How many days back to check
- `sample_rate`: Fraction of decisions to validate (0.0-1.0)

**Returns:** ValidationResult object

---

### ValidationResult

Result object from `validate_replay()`.

```python
results = validator.validate_replay()

print(results.total_checked)  # Total decisions checked
print(results.accurate)       # Number accurate
print(results.drifted)        # Number drifted
print(results.missing)        # Number missing
print(results.accuracy)       # Accuracy percentage
print(results.details)        # List of detailed results
```

---

## Compressor

Compress memory entries.

```python
from agent_memory_kit import Compressor, CompressionConfig

config = CompressionConfig(
    strategy="semantic",
    preserve_fields=["decision", "learning"]
)
compressor = Compressor(config)
```

### Compression Strategies

#### `"semantic"` (default)
Keep semantically important parts.

- Keeps: decisions, errors, learnings, configs
- Removes: chatter, redundant info

#### `"summarization"`
Create concise summaries.

- Truncates long text
- Summarizes lists
- Extracts key points

#### `"extraction"`
Keep only specified fields.

```python
config = CompressionConfig(
    strategy="extraction",
    preserve_fields=["decision", "outcome"]
)
```

---

## Best Practices

### Layer Selection Guide

| Data Type | Layer | Reason |
|-----------|-------|--------|
| Current task | HOT | Frequently accessed, temporary |
| User preferences | WARM | Persisted, regularly accessed |
| Old conversations | COLD | Archived, rarely needed |
| Active project files | HOT | Current work |
| Project history | COLD | Completed work |
| Settings/config | WARM | Persisted, moderate access |

### Performance Tips

1. **Use HOT for high-frequency access**
   ```python
   # Bad: Disk I/O every iteration
   for i in range(1000):
       data = memory.warm("config")
   
   # Good: Memory access
   memory.hot("config_cache", memory.warm("config"))
   for i in range(1000):
       data = memory.hot("config_cache")
   ```

2. **Batch COLD operations**
   ```python
   # Bad: Many small COLD writes
   for item in items:
       memory.cold(f"item_{item['id']}", item)
   
   # Good: One batch write
   memory.cold("batch_items", items)
   ```

3. **Compress regularly**
   ```python
   # Daily compression
   if datetime.now().hour == 0:  # Midnight
       memory.compress()
   ```

---

## Error Handling

All methods raise standard Python exceptions:

```python
try:
    memory.warm("key", large_data)
except MemoryError:
    # Handle memory limit exceeded
    memory.compress()
    memory.warm("key", large_data)
except PermissionError:
    # Handle file permission issues
    print("Cannot write to workspace")
except Exception as e:
    print(f"Unexpected error: {e}")
```
