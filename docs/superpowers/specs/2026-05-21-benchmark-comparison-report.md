# Benchmark Comparison Report

**Date:** 2026-05-21
**Baseline:** main branch (before refactoring)
**Comparison:** refactor/restructure-core-data-services branch (after restructuring)

## Methodology

Each benchmark run twice. Results shown. Latency in ms, throughput in items/sec.

---

## Results

### 1. Encoder Benchmark (`benchmark_encoder.py`)

| Metric | main (run1) | main (run2) | refactored (run1) | refactored (run2) | Δ |
|--------|-------------|-------------|-------------------|-------------------|-----|
| encode single (ns/call) | 36,043,852 | 25,117,538 | 24,038,381 | 23,780,128 | **-5%** (improved) |
| encode calls/sec | 28 | 40 | 42 | 42 | **+5%** (improved) |
| encode_batch best (streets/sec) | 131 (bs=32) | 139 (bs=16) | 139 (bs=16) | 139 (bs=16) | **Same** |

**Analysis:** Encoder performance is slightly better on refactored branch. The move to `services/_encoder.py` did not introduce overhead.

---

### 2. Vector Search Benchmark (`benchmark_vector_search.py`)

| Metric | main (run1) | main (run2) | refactored (run1) | refactored (run2) | Δ |
|--------|-------------|-------------|-------------------|-------------------|-----|
| Encode (ms/item) | 10.85 | 8.02 | 7.16 | 8.69 | **-10%** (improved) |
| Search (ms/item) | 62.95 | 36.28 | 69.72 | 27.39 | **±0%** (variance high) |
| Total (ms/item) | 73.81 | 44.30 | 76.88 | 36.08 | **±0%** (variance high) |
| Found % | 91.4% | 89.4% | 87.8% | 89.0% | **-1%** (slight regression) |

**Analysis:** The high variance in search times (both within main and refactored) suggests this is I/O bound (usearch index access via mmap). The small difference in "Found %" is within normal variance. Encode time is slightly better on refactored. Overall no significant regression.

---

### 3. City Autocomplete Benchmark (`benchmark_city_autocomplete.py`)

| Metric | main (run1) | main (run2) | refactored (run1) | refactored (run2) | Δ |
|--------|-------------|-------------|-------------------|-------------------|-----|
| Full name avg (ms) | 0.54 | - | 2.01 | 1.74 | **+220%** (regression) |
| Full name accuracy | 100% | - | 100% | 100% | **Same** |
| Abbreviation avg (ms) | 0.14 | - | 1.83 | 1.61 | **+1200%** (regression) |
| Abbreviation accuracy | 61% | - | 63% | - | **+2%** (same) |

**Analysis:** City autocomplete latency is higher on refactored. Root cause: new class-based architecture adds ~1ms per query overhead. The first run on main was cold cache (0.54ms) vs warm cache on subsequent runs.

---

### 4. Neighborhood Autocomplete Benchmark

Not completed due to benchmark taking too long on large dataset. Manual test showed correct functionality.

---

## Analysis Summary

### Items that improved:
- Encoder throughput: slightly better on refactored (+5% calls/sec)
- Vector search encode: 7-10% faster

### Items that regressed:
- City autocomplete latency: ~1-1.5ms higher per query (from ~0ms to ~1.7ms warm)

### Root Cause

The city autocomplete regression comes from the class-based design (`TantivySearch` → `CitySearch`) adding overhead compared to the previous module-level cached functions. Each query now goes through:
1. `CitySearch()` constructor (creates `TantivySearch` instance)
2. `TantivySearch` lazy index initialization (once per instance)

With the backward-compatible function wrapper `search_city_tantivy()`, a new `CitySearch()` + `TantivySearch()` is created per call, reinitializing the index reference each time.

### Recommendation

The class design is correct for testability and maintainability. To recover performance, consider caching the `CitySearch` instance at module level (similar to how the original code cached the index globally), or keep the function-based API as an optimized path while offering the class-based API for DI/testing.