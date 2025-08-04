# Search/Mode/State Architecture Unification Agent Prompt

Deploy 6 agents to streamline search, mode, and state architecture in this Vue 3/Pinia application. Ultrathink.

## DISCOVERY PHASE (2 agents)
- **Agent 1**: Research Vue 3 Composition API and Pinia best practices, analyze our store patterns, identify anti-patterns
- **Agent 2**: Map all search modes (lookup/wordlist/word-of-the-day/stage), their states, submodes, and transitions

## INVESTIGATION PHASE (4 agents)
- **Agent 3**: Analyze searchbar state fragmentation across stores (search-bar, search-config, search-results, content)
- **Agent 4**: Hunt mode-specific logic scattered across components, find consolidation opportunities
- **Agent 5**: Identify state duplication, circular dependencies, unnecessary re-renders
- **Agent 6**: Research control flow - who owns what state, who updates what, find violations of single responsibility

## SYNTHESIS
Create mode-centric architecture plan:
1. Each mode encapsulates: config, UI state, search state, content state
2. Clear ownership boundaries (what belongs where)
3. Unified state transitions and mode switching
4. Eliminate cross-store dependencies

Generate subplans for:
- Store consolidation strategy
- Component refactoring sequence
- State migration path
- Type safety improvements

No legacy patterns. Direct refactoring only. Mode-specific code lives in mode-specific modules. Shared code lives in composables. Be spartan - if it's not essential, delete it.

**Output**: Executable refactoring plan with clear ownership model and migration steps.