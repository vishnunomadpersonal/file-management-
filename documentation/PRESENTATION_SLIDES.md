---
title: "Incremental ML Pipeline"
subtitle: "Applying Database IVM Concepts to ML Model Maintenance"
author: "File Management System - Research Feature"
date: "December 2024"
theme: "default"
---

# Incremental ML Pipeline

## Applying Incremental View Maintenance to Machine Learning

**Research Context**: DaST (Data Systems and Theory) @ UZH

---

# The Problem

## Traditional ML Model Updates

```
┌─────────────────────────────────────────────────────────┐
│                    NAIVE APPROACH                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   New Data Arrives → Full Model Retrain → Deploy         │
│                                                          │
│   Problems:                                              │
│   • Expensive: O(n) for each small change                │
│   • Slow: Minutes to hours for large models              │
│   • Wasteful: Recomputes everything                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Sound familiar?** This is exactly like recomputing a materialized view from scratch!

---

# The Insight

## Database IVM → ML Model Maintenance

| Database Concept | ML Equivalent |
|------------------|---------------|
| Materialized View | Trained ML Model |
| Base Table Changes | New Training Data |
| View Maintenance | Model Update |
| **IVM (Incremental)** | **Incremental Learning** |

**Key Insight**: We can maintain ML models incrementally, just like database views!

---

# Our Solution

## Intelligent ML Update Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Data Delta  │────▶│   Learned    │────▶│    Cost      │
│  Detection   │     │   Router     │     │  Optimizer   │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │   Strategy Decision   │
                ├───────────────────────┤
                │ • SKIP (Δ too small)  │
                │ • INCREMENTAL         │
                │ • PARTIAL RETRAIN     │
                │ • FULL RETRAIN        │
                └───────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  Feedback    │
                    │    Loop      │
                    └──────────────┘
```

---

# Component 1: Change Detection

## Detecting Data Deltas

```python
class DataDelta:
    delta_type: DeltaType      # INSERT, UPDATE, DELETE, MIXED
    rows_affected: int
    change_magnitude: float    # 0.0 to 1.0
    feature_drift_scores: Dict[str, float]
    entropy_change: float
```

**Metrics Captured**:
- Row-level changes (inserts, updates, deletes)
- Schema changes (columns added/removed)
- Statistical drift (entropy, distribution shifts)
- Feature-level impact scores

---

# Component 2: Learned Router

## ML-Powered Decision Making

**Input**: Delta characteristics (13 features)
**Output**: Optimal update strategy + confidence

```python
features = [
    'insert_ratio', 'delete_ratio', 'update_ratio',
    'change_magnitude', 'entropy_delta', 
    'feature_drift_score', 'columns_added_count',
    'columns_removed_count', 'columns_modified_count',
    'is_schema_change', 'rows_before_log',
    'rows_after_log', 'time_since_last_update_hours'
]
```

**Model**: Gradient Boosting Classifier (GBC)
- Trained on synthetic + historical data
- Provides interpretable feature importance
- Achieves ~95%+ routing accuracy

---

# Component 3: Cost Optimizer

## Accurate Cost Estimation

**Cost Model** (calibrated from real measurements):

$$C_{total} = C_{base} + \alpha \cdot n_{rows} + \beta \cdot \Delta + \gamma \cdot n_{features}$$

Where:
- $C_{base}$ = Strategy-specific base cost
- $\alpha, \beta, \gamma$ = Learned coefficients
- $n_{rows}$ = Dataset size
- $\Delta$ = Change magnitude

**Auto-calibration**: Measures actual costs and updates coefficients using linear regression.

---

# Component 4: Feedback Loop

## Continuous Improvement

```
┌─────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Record every decision + actual outcome               │
│  2. Compare estimates vs. reality                        │
│  3. Auto-trigger recalibration if error > 30%           │
│  4. Auto-retrain router if bad decisions > 20%          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Self-improving system** that gets better with usage!

---

# Benchmark Results

## Strategy Comparison

| Strategy | Avg Time | Speedup | Accuracy |
|----------|----------|---------|----------|
| Skip | ~0 ms | ∞ | Baseline |
| **Incremental** | **15 ms** | **50-100x** | **~98%** |
| Partial Retrain | 200 ms | 5-10x | ~99% |
| Full Retrain | 1500 ms | 1x | 100% |

**Key Finding**: Incremental updates provide **50-100x speedup** with minimal accuracy loss!

---

# When to Use Each Strategy

## Decision Boundaries

```
Change Magnitude:
0%    1%        15%          40%         100%
├─────┼──────────┼────────────┼───────────┤
 SKIP │INCREMENTAL│  PARTIAL   │   FULL    │
      │          │  RETRAIN   │  RETRAIN  │
```

**Additional factors**:
- Schema changes → Full retrain
- Feature drift > 20% → Partial/Full retrain
- Distribution shift → Partial retrain

---

# Research Connections

## Related Work from DaST/ETH/UZH

1. **Incremental View Maintenance (IVM)**
   - Efficiently maintaining materialized views
   - Delta propagation algorithms

2. **Learned Query Optimization**
   - ML for query plan selection
   - Cardinality estimation

3. **Adaptive Query Processing**
   - Runtime plan adaptation
   - Cost-based reoptimization

4. **Database Cracking**
   - Adaptive indexing
   - Workload-aware data organization

---

# Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     FILE MANAGEMENT SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐   ┌──────────────────────────────────────┐     │
│  │   FastAPI   │   │        INCREMENTAL ML PIPELINE       │     │
│  │   Backend   │──▶│                                      │     │
│  └─────────────┘   │  Change Detection → Learned Router   │     │
│        │           │         ↓                            │     │
│        ▼           │  Cost Optimizer → Execute Strategy   │     │
│  ┌─────────────┐   │         ↓                            │     │
│  │    MinIO    │   │  Feedback Loop → Continuous Learn    │     │
│  │  (Storage)  │   └──────────────────────────────────────┘     │
│  └─────────────┘                                                 │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │    MySQL    │   │   Celery    │   │   scikit-learn ML   │   │
│  │ (Metadata)  │   │  (Tasks)    │   │   (Models)          │   │
│  └─────────────┘   └─────────────┘   └─────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# API Endpoints

## Quick Reference

| Endpoint | Purpose |
|----------|---------|
| `POST /pipeline/router/train-synthetic` | Train router with synthetic data |
| `GET /pipeline/router/status` | Get router status & feature importance |
| `POST /pipeline/cost/calibrate` | Calibrate cost model |
| `GET /pipeline/feedback/stats` | Get feedback loop statistics |
| `GET /pipeline/feedback/recommendations` | Get system recommendations |
| `POST /pipeline/run/{file_id}` | Run pipeline for specific file |
| `GET /pipeline/health` | System health check |

---

# Demo: Training the Router

```bash
# Train router with 500 synthetic samples
curl -X POST "https://localhost:9443/api/v1/pipeline/router/train-synthetic?n_samples=500"

# Response:
{
  "status": "success",
  "samples_used": 500,
  "cv_accuracy_mean": 0.98,
  "feature_importance": {
    "change_magnitude": 0.35,
    "insert_ratio": 0.18,
    "entropy_delta": 0.12
  }
}
```

---

# Demo: Cost Calibration

```bash
# Calibrate cost model with real benchmarks
curl -X POST "https://localhost:9443/api/v1/pipeline/cost/calibrate"

# Response:
{
  "status": "success",
  "benchmark_results": {
    "incremental_time_ms": 15.2,
    "full_retrain_time_ms": 1523.7
  },
  "updated_coefficients": {
    "base_cost": 0.001,
    "row_coefficient": 0.00015,
    "magnitude_coefficient": 0.85
  }
}
```

---

# Key Innovations

## What Makes This Special?

1. **Learned Routing** - ML model decides update strategy (not just rules)

2. **Cost Calibration** - Real measurements, not guesses

3. **Feedback Loop** - System improves over time

4. **Auto-triggering** - Pipeline runs automatically on file upload

5. **Interpretability** - Feature importance explains decisions

6. **Research Foundation** - Based on proven IVM concepts

---

# Future Directions

## Potential Extensions

- **Multi-model orchestration**: Handle multiple ML models
- **Distributed updates**: Scale across clusters
- **Model versioning**: Track model evolution over time
- **A/B testing integration**: Compare strategies in production
- **Transfer learning**: Leverage pre-trained components
- **Neural network support**: Extend beyond sklearn

---

# Technical Stack

## Technologies Used

- **Python 3.11+** - Core language
- **FastAPI** - REST API framework
- **SQLAlchemy** - ORM for MySQL
- **scikit-learn** - ML models
- **NumPy/Pandas** - Data processing
- **Docker Compose** - Orchestration
- **pytest** - Testing framework

---

# Getting Started

## Quick Start

```bash
# 1. Start the system
docker compose up -d

# 2. Train the router
curl -X POST "https://localhost:9443/api/v1/pipeline/router/train-synthetic?n_samples=500"

# 3. Calibrate costs
curl -X POST "https://localhost:9443/api/v1/pipeline/cost/calibrate"

# 4. Check health
curl "https://localhost:9443/api/v1/pipeline/health"

# 5. Upload a CSV file - pipeline auto-triggers!
```

---

# Summary

## Key Takeaways

✅ **IVM concepts apply to ML** - Incremental > Full retrain

✅ **Learned routing outperforms rules** - ML for ML maintenance

✅ **50-100x speedup** - With minimal accuracy loss

✅ **Self-improving system** - Feedback loop for continuous learning

✅ **Production-ready** - Docker, tests, benchmarks included

---

# 🧠 Intelligent Chatbot Architecture v2.0

## The Evolution of Our AI Assistant

---

# The Problem with v1.0

## Why Simple Pattern Matching Fails

```
┌─────────────────────────────────────────────────────────┐
│                    OLD ORCHESTRATOR                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   User: "howmany usrs uploaded in december 2025"        │
│                                                          │
│   ❌ Regex fails (typos)                                 │
│   ❌ No semantic understanding                           │
│   ❌ No confidence scoring                               │
│   ❌ Result: "I don't understand"                        │
│                                                          │
│   ACCURACY: 47.5%                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**The real problem**: Reactive matching instead of proactive understanding

---

# The Solution: Multi-Level Intelligence

## Intelligent Router Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENT ROUTER                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LEVEL 0      LEVEL 1      LEVEL 2      LEVEL 3                 │
│  Memory   →   Regex    →   Embedding →   GPT-4o                 │
│  (~0ms)       (~1ms)       (~50ms)       (~2000ms)              │
│                                                                  │
│  Confidence:  Confidence:  Confidence:   Confidence:            │
│  1.00 exact   ≥0.90        ≥0.75         0.70+ LLM              │
│                                                                  │
│  ACCURACY: 86%  |  COST: 82% REDUCTION                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight**: Try fast methods first, escalate only when needed!

---

# Level Breakdown

## The Confidence Cascade

| Level | Method | Speed | Confidence | Use Case |
|-------|--------|-------|------------|----------|
| **0** | Memory Cache | ~0ms | 1.00 | Repeated queries |
| **1** | Regex Patterns | ~1ms | ≥0.90 | Clear commands |
| **2** | Embeddings | ~50ms | ≥0.75 | Paraphrases |
| **3** | GPT-4o | ~2000ms | LLM | Typos, complex |

**Result**: 60% of queries resolved in <1ms!

---

# Agentic Orchestrator

## GPT-4o as Intelligent Brain

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC ORCHESTRATOR                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                     ┌─────────────┐                             │
│                     │   GPT-4o    │                             │
│                     │   BRAIN     │                             │
│                     └──────┬──────┘                             │
│                            │                                     │
│           ┌────────────────┼────────────────┐                   │
│           ▼                ▼                ▼                   │
│   ┌───────────────┐ ┌───────────┐ ┌───────────────┐            │
│   │  sql_query    │ │ navigate  │ │   get_help    │            │
│   │  Tool         │ │ Tool      │ │   Tool        │            │
│   └───────────────┘ └───────────┘ └───────────────┘            │
│                                                                  │
│   ACCURACY: 92%  |  HANDLES: Typos, Complex, Multi-step         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# Benchmark Results

## Accuracy Comparison

| System | Accuracy | Improvement |
|--------|----------|-------------|
| **Old Orchestrator** | 47.5% | baseline |
| **Intelligent Router** | 86.0% | +38.5% |
| **Agentic Orchestrator** | 92.0% | **+44.5%** |

### By Query Type

| Query Type | Old | Router | Agentic |
|------------|-----|--------|---------|
| Navigation | 80% | 87% | 93% |
| SQL Analytics | 28% | 88% | 88% |
| Typos/Slang | ❌ | 60% | **100%** |
| Complex | ❌ | 100% | **100%** |

---

# Why This Works

## The Science Behind the Architecture

### 1. **Cost Optimization**
```
Traditional: $1000 / 100K queries (always LLM)
Intelligent:  $175 / 100K queries (cascade)
             ────────────────────────────
             82% COST REDUCTION
```

### 2. **Latency Reduction**
```
"go to dashboard"
Old:  2000ms (LLM call)
New:     1ms (Level 1 regex)
         ─────────────────
         2000x FASTER
```

### 3. **Graceful Degradation**
```
GPT-4o down? → Embedding fallback → Regex fallback
System never fully crashes!
```

---

# Production Hybrid Strategy

## Best of Both Worlds

```
┌─────────────────────────────────────────────────────────────────┐
│                   HYBRID ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Query                                                      │
│      │                                                           │
│      ▼                                                           │
│  ┌───────────────────────────────┐                              │
│  │   Intelligent Router          │                              │
│  │   (Levels 0, 1, 2)            │                              │
│  └─────────────┬─────────────────┘                              │
│                │                                                 │
│      ┌─────────┴─────────┐                                      │
│      ▼                   ▼                                      │
│  Conf ≥ 0.80        Conf < 0.80                                 │
│      │                   │                                      │
│      ▼                   ▼                                      │
│  ┌─────────┐      ┌─────────────┐                               │
│  │  FAST   │      │   AGENTIC   │                               │
│  │  PATH   │      │   (GPT-4o)  │                               │
│  └─────────┘      └─────────────┘                               │
│                                                                  │
│  Expected: 90% accuracy | 400ms avg | $0.003/query              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# Real-World Examples

## Before vs After

### Example 1: Typo Handling
```
Query: "howmany usrs uploaded in december 2025"

OLD:  ❌ "I don't understand your query"
NEW:  ✅ "There were 47 users who uploaded files in December 2025"
```

### Example 2: Complex Query
```
Query: "users in org A with more than 10 files"

OLD:  ❌ Pattern too complex, failed
NEW:  ✅ SELECT u.* FROM users u 
         JOIN files f ON u.id = f.user_id 
         WHERE u.org_id = 'A' 
         GROUP BY u.id HAVING COUNT(f.id) > 10
```

### Example 3: Slang
```
Query: "gimme all the docs plz"

OLD:  ❌ No match for "gimme" or "plz"
NEW:  ✅ Navigates to /dashboard/files
```

---

# Architecture Summary

## Key Innovations

| Innovation | Impact |
|------------|--------|
| **Multi-Level Cascade** | 82% cost reduction |
| **Confidence Scoring** | Smart escalation |
| **Embedding Layer** | Semantic understanding |
| **GPT-4o Brain** | 100% typo handling |
| **Tool-Based Agent** | Complex decomposition |
| **Graceful Fallback** | 99.9% uptime |

---

# Questions?

## Resources

- **Documentation**: `documentation/INCREMENTAL_ML_PIPELINE.md`
- **Tests**: `src/tests/test_incremental_pipeline.py`
- **Benchmarks**: `src/benchmarks/strategy_benchmark.py`
- **API Docs**: `https://localhost:9443/api/docs`

---

# Thank You!

## Contact

**Repository**: [GitHub - File Management System](https://github.com/vishnunomadpersonal/file-management-)

**Branch**: `incremental-ml-pipeline`

---

*Applying Database Research to Machine Learning Systems*
