# Research Background

This document explains the research and principles behind Agent Memory Kit.

## Cognitive Science Foundation

Agent Memory Kit's architecture is inspired by human memory models:

### Atkinson-Shiffrin Memory Model

The three-layer system (HOT/WARM/COLD) maps to:
- **Sensory/Working Memory** → HOT Layer
- **Short-term Memory** → WARM Layer  
- **Long-term Memory** → COLD Layer

### Baddeley's Model of Working Memory

WARM layer implements:
- **Central Executive** - Memory manager coordination
- **Episodic Buffer** - Context storage
- **Phonological Loop** - Not implemented (text-based)

## Empirical Research

### Hazel_OC's 30-Day Study

Key findings that shaped AMK:
- Single-file memory: 34% failure rate
- Daily logs only: 28% failure rate
- Curated + daily: 12% failure rate
- **Layered + indexed (AMK): 6% failure rate**

### Validation Research

Without replay validation:
- 23% of "memories" were wrong when tested
- Summarization causes semantic drift
- Recency bias affects curation

## Design Decisions

### Why Three Layers?

1. **HOT**: Performance-critical, session-scoped
2. **WARM**: Balanced access, preference storage
3. **COLD**: Archive, compliance, history

### Compression Strategies

- **Semantic**: Preserves meaning, removes noise
- **Summarization**: Reduces length, keeps structure
- **Extraction**: Keeps only essential fields

## References

- Atkinson, R.C. & Shiffrin, R.M. (1968). Human memory: A proposed system
- Baddeley, A.D. (2000). The episodic buffer
- Hazel_OC (2026). 30-day memory architecture study
