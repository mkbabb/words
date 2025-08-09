# Frontend Refactoring Priority Matrix

## 🔴 Critical Priority (Blocking Issues)

### Components Requiring Immediate Refactoring
| Component | Current Lines | Target Lines | Issues | Action |
|-----------|--------------|--------------|--------|--------|
| `Home.vue` | 327 | 50 | Mixed routing/state/UI logic | Split into routes + App.vue |
| `SearchBar.vue` | 740 | 150 | Monolithic, 15+ responsibilities | Extract 8+ sub-components |
| `DefinitionDisplay.vue` | 563 | 100 | Complex rendering, mixed concerns | Decompose into hierarchy |
| `WordListView.vue` | 597 | 150 | Client-side processing, duplicate versions | Server-side + mode separation |
| `SearchControls.vue` | 462 | 50 | All modes in one component | Mode-specific components |

### Stores Requiring Consolidation
| Store | Action | Reason |
|-------|--------|--------|
| `search-bar.ts` + `content.ts` | Merge into `search.ts` | Duplicate delegation logic |
| Mode content stores | Delete | Unnecessary abstraction layer |
| `loading.ts` | Convert to composable | Over-engineered for simple state |
| `notifications.ts` | Convert to composable | Simple toast logic |

## 🟡 High Priority (Performance & Maintainability)

### API Layer Refactoring
| File | Issue | Solution |
|------|-------|----------|
| `useSearchOrchestrator.ts` | 414 lines mixing concerns | Split into mode handlers |
| `lookup.ts` + `ai.ts` | Duplicate SSE logic (400+ lines) | Unified SSE client |
| `api.ts` | 15+ methods in single object | Focused API clients |

### Component Improvements
| Component | Issue | Quick Win |
|-----------|-------|-----------|
| `ProgressiveSidebar.vue` | Over-complex composables | Direct implementation |
| `SidebarContent.vue` | Duplicate mode logic | Dynamic component routing |
| `ExampleList.vue` + `ExampleListEditable.vue` | Duplicate components | Single component with mode prop |

## 🟢 Medium Priority (Architecture Enhancement)

### New Components to Create
```
Priority Order:
1. SearchInput.vue - Extract from SearchBar
2. ModeRouter.vue - Handle mode switching
3. DefinitionHeader.vue - Extract from DefinitionDisplay
4. WordListStats.vue - Extract from WordListView
5. FilterBuilder.vue - Unified filtering UI
```

### Performance Optimizations
```
1. Virtual scrolling for WordListView
2. Lazy loading for route components  
3. Skeleton components for loading states
4. Shallow refs for large arrays
5. Memoized expensive computations
```

## 📊 Refactoring Metrics

### Code Reduction Targets
- **Total Frontend LOC**: ~15,000 → ~10,000 (33% reduction)
- **Component Average**: 250 lines → 100 lines
- **Store Complexity**: 10 stores → 5 stores
- **API Methods**: 50+ methods → 20 focused methods

### Complexity Reduction
| Metric | Current | Target |
|--------|---------|--------|
| Max component size | 740 lines | 150 lines |
| Avg cyclomatic complexity | 15 | 5 |
| Max prop count | 12 | 5 |
| Max import count | 20 | 8 |

## 🚀 Quick Wins (< 30 min each)

1. **Extract DefinitionHeader**: Lines 1-80 of DefinitionDisplay
2. **Create SearchInput**: Lines 150-250 of SearchBar  
3. **Merge duplicate ExampleList components**
4. **Extract WordListStats**: Statistics display logic
5. **Convert notifications to composable**

## ⚠️ Risk Areas

### High Risk Refactors
- **SearchBar decomposition**: Core functionality, needs careful testing
- **Store consolidation**: State management is critical path
- **Route restructuring**: Could break deep links

### Mitigation Strategy
1. Write comprehensive tests first
2. Create feature flags for gradual rollout
3. Keep old components during transition
4. Monitor error rates closely

## 📈 Success Metrics

### Immediate Improvements
- 50% reduction in largest component sizes
- 30% fewer store dependencies
- 40% less prop drilling

### Long-term Benefits  
- 70% faster build times
- 80% reduction in component test complexity
- 90% improvement in new feature velocity

## 🎯 Implementation Sequence

### Week 1 Focus
1. Create unified SSE client
2. Consolidate search/content stores
3. Extract SearchInput component
4. Split Home.vue into routes

### Week 2 Focus  
1. Decompose DefinitionDisplay
2. Modularize SearchControls
3. Implement virtual scrolling
4. Create mode-specific sidebars

### Week 3 Focus
1. Complete API layer refactoring
2. Add comprehensive tests
3. Performance optimization
4. Documentation updates