# Meta Prompt for Git History Cleanup Execution

## **Core Principles**
- **Content-first messaging**: Focus on WHAT changed, not HOW it was implemented
- **Atomic commits**: Each commit should represent a single logical change
- **Pithy precision**: Maximum 50 characters for commit title, zero fluff
- **Functional clarity**: Message should answer "What does this commit accomplish?"

## **Commit Splitting Guidelines**

### **Logical Boundaries for Large Commits**
1. **Backend/Frontend separation**: Never mix in same commit
2. **Feature boundaries**: One feature enhancement per commit
3. **File type grouping**: Models, API routes, components, styles
4. **Dependency changes**: Separate from feature code
5. **Configuration**: Docker, scripts, build configs standalone

### **Split Decision Framework**
```
IF commit touches > 10 files OR > 500 lines:
  ├── Group by functional area (API, UI, models, etc.)
  ├── Separate configuration from code changes  
  ├── Extract dependency updates
  └── Create focused commits per area

IF multiple features in one commit:
  └── Split by user-facing functionality
```

## **Message Writing Rules**

### **Format Template**
```
<type>: <imperative description>

[Optional body: WHY this change, not what files changed]
```

### **Type Categories**
- `feat`: New user-facing functionality
- `fix`: Bug resolution  
- `refactor`: Code restructure without behavior change
- `perf`: Performance improvement
- `build`: Build system, dependencies, tooling
- `docs`: Documentation only

### **Message Standards**
- **Imperative mood**: "add", "fix", "implement" (not "added", "fixing")
- **No periods**: `feat: add user authentication` ✓
- **No redundancy**: ~~"update API to add new endpoint"~~ → `feat: add user lookup endpoint`
- **Focus on outcome**: ~~"refactor database code"~~ → `refactor: extract database connection pool`

### **Forbidden Patterns**
- ❌ Implementation details: "update useSearchBarState composable"
- ❌ Vague terms: "cleanup", "fixes", "updates", "changes"  
- ❌ Version indicators: "v2", "v3", "WIP", "partial impl"
- ❌ Tool references: "claude", "generated", "🤖"
- ❌ Redundant prefixes: "update X to do Y" → "do Y"

## **Execution Workflow**

### **For Each Commit Being Split**
1. **Analyze**: `git show --stat <commit>` - understand scope
2. **Reset**: `git reset HEAD~1` - unstage the commit
3. **Group**: `git add -p` - selectively stage by logical groups
4. **Commit**: Apply pithy message following template
5. **Repeat**: Until all changes committed in logical chunks

### **Message Quality Check**
Before each commit, ask:
- Does this explain the user-facing impact?
- Could a new developer understand the purpose?
- Is every word necessary?
- Does it follow imperative mood?

### **Example Transformations**
| Original | Transformed |
|----------|-------------|
| "wordlist refactor and partial impl v3" | `refactor: extract wordlist repository pattern` |
| "PWA impl & c" | `feat: implement offline Progressive Web App` |
| "cleanup & c" | `refactor: remove unused imports and dead code` |
| "backend typing, searchbar refactor" | Split: `refactor: add type annotations to API layer` + `refactor: extract search component logic` |

## **Quality Gates**
- Each commit builds successfully
- Each commit has single logical purpose  
- Message explains the "why" or "what", never the "how"
- No commit touches both backend and frontend
- No Claude authorship text remains

**Execute with precision. Every commit message is a future developer's first impression of the change.**