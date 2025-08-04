# Type System Unification & Streamlining Agent Prompt

Deploy 6 agents in parallel to analyze and unify the TypeScript type system across this Vue 3 codebase. Ultrathink.

## RESEARCH PHASE (2 agents)
- **Agent 1**: Scan package.json, identify core dependencies (Vue 3, Pinia, Vite), research modern TypeScript best practices for these frameworks
- **Agent 2**: Analyze import patterns, identify most-used types, create dependency graph

## ANALYSIS PHASE (4 agents)
- **Agent 3**: Hunt duplicate type definitions across /types, /stores/types, /components/**/types
- **Agent 4**: Identify component-specific vs shared types, find opportunities for generalization
- **Agent 5**: Analyze 'any' usage, missing type safety, implicit types that should be explicit
- **Agent 6**: Research type hierarchies, find inheritance opportunities, identify redundant interfaces

## SYNTHESIS
Generate comprehensive refactoring plan with:
1. Types to consolidate (duplicates)
2. Types to promote (local → global)
3. Types to create (missing abstractions)
4. Types to eliminate (redundant/unused)

Be indefatigable. KISS principle paramount. Every type should have ONE canonical location. Component props stay local, data models go global. No backwards compatibility - refactor at the root.

**Output**: Actionable plan with file paths, type names, and specific transformations.