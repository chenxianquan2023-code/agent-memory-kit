# Quick Start Guide

Get up and running with Agent Memory Kit in 5 minutes.

## Installation

```bash
pip install agent-memory-kit
```

## Your First Memory

```python
from agent_memory_kit import MemoryManager

# Create a memory manager
memory = MemoryManager(workspace="./my_first_agent")

# Store something in HOT layer (current session)
memory.hot("current_task", "Learning AMK")

# Store in WARM layer (persistent preferences)
memory.warm("my_name", "Alice")

# Store in COLD layer (archive)
memory.cold("first_session_notes", "Today I learned about HOT/WARM/COLD layers")

# Retrieve
print(memory.hot("current_task"))  # "Learning AMK"
print(memory.warm("my_name"))      # "Alice"
```

## Understanding the Layers

### ⚡ HOT Layer

**Use for:** Current session data, active work

```python
# Store current conversation
memory.hot("chat_history", ["Hello!", "How can I help?"])

# Update frequently
chat = memory.hot("chat_history")
chat.append("Thanks!")
memory.hot("chat_history", chat)
```

**Characteristics:**
- ✅ Always in memory (fastest)
- ❌ Lost after session ends
- 📏 Max ~200 entries recommended

### 🔥 WARM Layer

**Use for:** User preferences, settings, ongoing projects

```python
# Store preferences once
memory.warm("code_style", "pythonic")
memory.warm("favorite_tools", ["pytest", "black", "mypy"])

# Retrieved many times, loaded once
for i in range(100):
    style = memory.warm("code_style")  # Fast after first load
```

**Characteristics:**
- ✅ Cached after first load
- ✅ Persisted between sessions
- 📏 Max ~500 entries recommended

### ❄️ COLD Layer

**Use for:** Old conversations, completed projects, archives

```python
# Archive old data
memory.cold("project_2024_01_final", project_data)

# Retrieve when needed (slower)
old_project = memory.cold("project_2024_01_final")
```

**Characteristics:**
- ✅ Unlimited storage
- ✅ Compressed automatically
- ⚠️ Slower to retrieve

## Best Practices

### 1. Choose the Right Layer

```python
# ✅ Good: Active work in HOT
memory.hot("files_being_edited", ["app.py", "models.py"])

# ✅ Good: Config in WARM
memory.warm("project_structure", {...})

# ✅ Good: Old data in COLD
memory.cold("meeting_notes_2024_02", {...})

# ❌ Bad: Everything in one layer
memory.hot("all_my_data_ever", huge_dict)  # Don't do this!
```

### 2. Compress Regularly

```python
# Run this periodically (e.g., daily)
stats = memory.compress()
print(f"Archived {stats['warm_to_cold']} old entries")
```

### 3. Validate Your Memory

```python
from agent_memory_kit import ReplayValidator

validator = ReplayValidator(memory)

# Log important decisions
validator.log_decision(
    context="Choosing database",
    decision="Selected PostgreSQL",
    result="Works well for our use case"
)

# Check accuracy weekly
results = validator.validate_replay(days=7)
if results.accuracy < 80:
    print("⚠️ Memory needs tuning!")
```

## Next Steps

- Read [Architecture](./ARCHITECTURE.md) for deep dive
- Check [Examples](../examples/) for real-world usage
- See [API Reference](./API.md) for all features

## Troubleshooting

### Issue: Memory not persisting

**Solution:** Make sure you're using WARM or COLD, not just HOT:

```python
# ❌ Lost after session
memory.hot("important_config", {...})

# ✅ Persisted
memory.warm("important_config", {...})
```

### Issue: Too slow

**Solution:** Use HOT layer for frequently accessed data:

```python
# ❌ Slow: Loading from disk every time
for i in range(1000):
    data = memory.warm("frequent_data")  # Disk I/O every time

# ✅ Fast: Keep in HOT
memory.hot("frequent_data", data)
for i in range(1000):
    data = memory.hot("frequent_data")  # Memory only
```

### Issue: Memory usage too high

**Solution:** Compress more aggressively:

```python
config = MemoryConfig(
    hot_max_lines=100,   # Reduce from 200
    warm_max_lines=300,  # Reduce from 500
    cold_compression_days=3  # Compress more often
)
memory = MemoryManager("./workspace", config)
```
