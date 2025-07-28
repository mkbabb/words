# Progressive Scrollbar Auto-Scroll Fix - Test Plan

## Implementation Summary

Fixed the bug where the progressive scrollbar would break when it needed to scroll itself. The fix implements:

1. **Auto-scroll detection**: Checks if clicked/active elements are visible within the sidebar container
2. **Smart scrolling**: Centers elements that are out of view within the sidebar
3. **Reactive tracking**: Automatically scrolls when active sections change due to content scrolling
4. **KISS principle**: Simple, single-purpose function handles all auto-scroll cases
5. **DRY principle**: One `scrollSidebarToElement` function handles both click and reactive scenarios

## Key Changes Made

### 1. ProgressiveSidebar.vue
- Added template ref `navContainer` for the scrollable nav element
- Implemented `scrollSidebarToElement()` function that:
  - Checks if element is already visible
  - Centers elements that are out of view
  - Uses smooth scrolling
- Added watchers for `activeCluster` and `activePartOfSpeech` to auto-scroll on changes
- Updated click handlers to ensure clicked elements stay visible

### 2. SidebarCluster.vue
- Added `data-sidebar-cluster` attribute to cluster buttons for targeting

### 3. SidebarPartOfSpeech.vue  
- Added `data-sidebar-pos` attribute to part-of-speech buttons for targeting

## Test Scenarios

### Manual Testing Steps:
1. Load a word with many definition clusters (>10)
2. Verify the sidebar shows scrollbar when content overflows
3. Click on a cluster at the bottom of the sidebar list
4. Verify the sidebar auto-scrolls to keep the clicked item visible
5. Scroll the main content and observe active section changes
6. Verify the sidebar auto-scrolls to keep the active section visible

### Expected Behavior:
- ✅ Sidebar should never lose track of active/clicked elements
- ✅ Smooth scrolling should center elements in the sidebar view
- ✅ No performance issues with frequent scroll events (debounced)
- ✅ Works for both cluster and part-of-speech navigation

## Technical Details

The fix handles the edge case where:
- Progressive scrollbar itself has many sections requiring internal scrolling
- User clicks on sections outside the visible area of the sidebar
- Content scrolling causes active section to change to one not visible in sidebar

The solution maintains the progressive nature while ensuring visibility of active elements.