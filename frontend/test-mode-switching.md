# Mode Switching Enhancement Test Plan

## Features Implemented

### 1. Enhanced Router Navigation
- ✅ `navigateToLookupMode(query, mode)` - Handles dictionary/thesaurus/suggestions sub-modes
- ✅ `navigateToWordlist(id, filters, query)` - Wordlist with filters and mode query
- ✅ `navigateToWordOfTheDay(query)` - Word-of-the-day with query
- ✅ `navigateToStage(query)` - Stage mode with query

### 2. Mode-Specific Query Storage
- ✅ Save current query to mode-specific storage before switching
- ✅ Restore mode-specific query after switching
- ✅ Maintain separate query states for lookup, wordlist, word-of-the-day, stage

### 3. Wordlist Mode Enhancements
- ✅ Include current filters in router navigation
- ✅ Pass mode query to wordlist route
- ✅ Support filter parameters in URL

## Test Scenarios

### Lookup Mode Switching
1. **Dictionary ↔ Thesaurus Toggle**
   - Set query "example" in dictionary mode
   - Toggle to thesaurus mode → Should navigate to `/thesaurus/example`
   - Toggle back to dictionary → Should navigate to `/definition/example`

2. **Suggestions Mode**
   - Set query "give me 10 words" in dictionary mode
   - Switch to suggestions → Should stay on home with `?q=give%20me%2010%20words&mode=suggestions`

### Mode Query Persistence
1. **Query Storage Between Modes**
   - Set query "hello" in lookup mode
   - Switch to wordlist mode → "hello" saved to lookup mode storage
   - Set query "my-list" in wordlist mode
   - Switch back to lookup → Should restore "hello"
   - Switch to wordlist → Should restore "my-list"

### Wordlist Mode Router Integration
1. **Wordlist with Filters and Query**
   - Set wordlist filters (e.g., difficulty level)
   - Set mode query "search-term"
   - Switch to wordlist mode → Should navigate to `/wordlist/{id}?q=search-term&filters=...`

### Cross-Mode Navigation
1. **Full Mode Cycle**
   - Start in lookup mode with query "test"
   - Toggle through: lookup → wordlist → word-of-the-day → stage → lookup
   - Each should maintain its own query and navigate appropriately

## Manual Testing Steps

### Setup
```javascript
// In browser console:
const { useStores } = window.Vue;
const { searchBar, searchConfig, ui, orchestrator } = useStores();
```

### Test 1: Dictionary/Thesaurus Toggle
```javascript
// Set up lookup mode with query
searchConfig.setSearchMode('lookup');
searchBar.setQuery('eloquent');
ui.setMode('dictionary');

// Navigate to dictionary
// Check URL: should be /definition/eloquent

// Toggle to thesaurus via ModeToggle component
ui.setMode('thesaurus');
// Check URL: should be /thesaurus/eloquent
```

### Test 2: Mode Query Persistence
```javascript
// Test query saving and restoration
searchBar.setQuery('lookup-query');
searchBar.saveModeQuery('lookup', 'lookup-query');

searchBar.setQuery('wordlist-query'); 
searchBar.saveModeQuery('wordlist', 'wordlist-query');

// Switch modes and verify restoration
const lookupQuery = searchBar.restoreModeQuery('lookup');
const wordlistQuery = searchBar.restoreModeQuery('wordlist');

console.log('Lookup query:', lookupQuery); // Should be 'lookup-query'
console.log('Wordlist query:', wordlistQuery); // Should be 'wordlist-query'
```

### Test 3: Enhanced Mode Switching
```javascript
// Test full mode switching with orchestrator
await orchestrator.setSearchMode('wordlist', router);
// Should save current query and navigate with filters

await orchestrator.toggleSearchMode(router);
// Should cycle to next mode with proper query restoration
```

## Expected Results

### Router State After Mode Changes
- **Lookup + Dictionary**: `/definition/{query}`
- **Lookup + Thesaurus**: `/thesaurus/{query}`  
- **Lookup + Suggestions**: `/?q={query}&mode=suggestions`
- **Wordlist**: `/wordlist/{id}?q={query}&filters={...}`
- **Word-of-the-day**: `/?mode=word-of-the-day&q={query}`
- **Stage**: `/?mode=stage&q={query}`

### Query Persistence
- Each mode maintains its own query state
- Switching modes saves current query and restores target mode query
- Router reflects the active mode query
- UI updates to show correct query for current mode

## Implementation Status
✅ **COMPLETE** - All core functionality implemented and tested