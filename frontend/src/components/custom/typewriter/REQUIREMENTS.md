# Typewriter Animation Requirements

## States
- `displayText`: What's currently shown on screen
- `targetText`: The text we want to display
- `isAnimating`: Whether animation is in progress

## Behavior

### Initial Load
- Start with empty `displayText`
- Type `targetText` character by character
- Speed: 60ms between characters

### When Target Text Changes
1. **Compare** `displayText` with new `targetText`
2. **Backspace** random amount (20-80% of `displayText.length`)
   - Each backspace takes 50ms
   - User sees: "hello" → "hell" → "hel" → "he"
3. **Pause** 300ms
4. **Clear** remaining characters (if any)
   - Each deletion takes 40ms  
5. **Type** new `targetText` from beginning
   - Speed: 120ms between characters (slower than initial)

## Critical Implementation Details
- **NEVER** set `displayText = ''` directly
- **NEVER** reset/clear on text prop change
- Backspace by doing `displayText = displayText.slice(0, -1)` in a loop with delays
- Each character removal must be visible to the user
- Use `requestAnimationFrame` or `setTimeout` for timing

## Example Flow
```
Current display: "hello"
New target: "world"

1. Backspace to "he" (3 chars @ 50ms each = 150ms)
2. Pause (300ms)
3. Clear to "" (2 chars @ 40ms each = 80ms)  
4. Type "world" (5 chars @ 120ms each = 600ms)
Total: 1130ms
```