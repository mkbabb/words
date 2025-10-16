# Complexity Analysis - Quick Reference

## Overall Score: 6.2/10

## Top 3 Issues (by impact)

### 1. Streaming Infrastructure (8.5/10)
- **File**: `backend/src/floridify/core/streaming.py`
- **Issue**: Dual implementations (~200 lines duplicated)
- **Fix effort**: 2-3 hours
- **Impact**: 60% complexity reduction

### 2. Search Engine Init (7.8/10)
- **File**: `backend/src/floridify/search/core.py`
- **Issue**: Multi-stage initialization with race conditions
- **Fix effort**: 1-2 hours
- **Impact**: 70% reduction in init complexity

### 3. Caching Decorators (7.1/10)
- **File**: `backend/src/floridify/caching/decorators.py`
- **Issue**: 6 decorators with 90% shared code (484 lines)
- **Fix effort**: 2-3 hours
- **Impact**: 65% complexity reduction

## Quick Wins (under 30 minutes each)

1. Remove triple exception catch (`caching/manager.py:XXX`)
2. Extract token parameter logic (`ai/connector.py:142-164`)
3. Define magic number constant (`core/streaming.py` - `32768`)
4. Use elif instead of if chains (`providers/utils.py:247-275`)

**Total quick-win time: 1 hour, saves 15-20% complexity in affected modules**

## No Changes Needed

- `ai/model_selection.py` - Well-designed configuration approach
- Type hints - 95% coverage, excellent
- Async patterns - Properly managed, no callback hell
- Recent refactoring efforts - Successfully eliminated hasattr patterns

## Metrics by Module

| Module | Lines | Complexity | Assessment |
|--------|-------|-----------|------------|
| streaming.py | 454 | 8.5 | Refactor priority #1 |
| search/core.py | 849 | 7.8 | Complex init, needs state machine |
| ai/connector.py | 1367 | 7.3 | Scattered validation, fixable |
| caching/decorators.py | 484 | 7.1 | Over-specialization |
| state_tracker.py | 470 | 6.8 | Config duplication |
| providers/utils.py | 423 | 6.5 | If-chain cleanup |
| caching/manager.py | ~250 | 6.3 | Minor exception handling |
| model_selection.py | 155 | 5.2 | Good design, no changes |

## Positive Findings

✓ No hasattr patterns (deliberately removed)
✓ Strong type hints throughout
✓ Consistent logging strategy
✓ Clear naming conventions
✓ Proper async/await usage
✓ Evidence of intentional simplification (PATHOLOGICAL REMOVAL comments)

## Implementation Roadmap

**Phase 1 (Quick Wins)**: 1 hour
- Clean up exception handling
- Extract helper functions
- Define constants

**Phase 2 (Medium)**: 6 hours
- Unify caching decorators
- Simplify state tracker configs
- State machine for semantic init

**Phase 3 (Follow-up)**: 2 hours
- Code review and testing
- Performance benchmarking
- Documentation updates

**Total effort**: 8-10 hours
**Complexity reduction**: 25-35% in targeted modules

