# WordList Requirements

## Problem
- Load More button causes full page re-render
- All existing cards flash/re-mount when new batch loads
- User explicitly stated: "still triggering a full re-render"

## Required Behavior
- Load More adds new cards without touching existing ones
- No flashing, no re-mounting of existing cards
- Smooth append of new items only

## Constraints
- Must keep sorting functionality
- Must keep search functionality  
- Cannot disable features - "No, we need sort and search"
- Solution must prevent "each batch does NOT cause a new page load or rerender"

## Current Implementation
- Using `currentWords` array with v-for
- Array mutations trigger full template re-evaluation
- All cards re-render despite unique keys

## Failed Attempts
- shallowRef
- Array mutations (push, splice)
- Unique stable keys
- Batched components
- v-memo directive