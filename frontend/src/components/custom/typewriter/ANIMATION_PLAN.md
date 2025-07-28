# Typewriter Animation Implementation Plan

## Overview
Create a human-like typewriter animation that shows realistic typing behavior including backspacing and retyping.

## Animation Behavior

### First Animation (when component mounts or text first appears)
1. Start with empty display
2. Type the text quickly using "expert" mode
3. No errors, no backspacing
4. Fast, efficient typing

### Subsequent Animations (when text changes while component is active)
1. **DO NOT** clear the existing text immediately
2. **Backspace Phase**:
   - Calculate how many characters to delete (random: 20-80% of current text length)
   - Animate the backspacing character by character
   - Each backspace should be visible (30-70ms delay between each)
   - The existing text should visibly shrink as characters are deleted
3. **Pause Phase**:
   - After backspacing, pause briefly (200-400ms)
   - This simulates human thinking/decision time
4. **Typing Phase**:
   - Start typing the NEW text from where the backspacing stopped
   - If we backspaced to position 5, start typing new text from position 5
   - Use the configured mode (human/expert/basic) for typing speed
   - Include natural variations and QWERTY-based delays

## Technical Requirements

### State Management
- Track whether this is the first animation (`isFirstAnimation`)
- Track the currently displayed text (`displayText`)
- Track whether we're currently animating (`isTyping`)
- **DO NOT** reset/clear displayText when new text arrives

### Text Change Detection
- When the `text` prop changes in TypewriterText component:
  - **DO NOT** call reset() 
  - **DO NOT** clear displayText
  - Let the animation handle the transition

### Key Functions
1. `startTyping()`:
   - Check if we have existing text
   - If yes, perform backspace animation
   - Then type the new text
   - Never immediately clear displayText

2. `animateBackspace(targetLength)`:
   - Gradually remove characters from displayText
   - Each removal should be visible with delay
   - Stop at targetLength

3. `animateTyping(startPosition)`:
   - Type new text starting from startPosition
   - If text was partially backspaced, append to existing text
   - If fully backspaced, type from beginning

## Example Scenarios

### Scenario 1: First load
- Display: "" (empty)
- New text: "hello"
- Action: Type "h-e-l-l-o" quickly

### Scenario 2: Text change
- Display: "hello"
- New text: "world"
- Action: 
  1. Backspace "hello" → "hel" (or "he" or "h", random)
  2. Pause
  3. Clear remaining text
  4. Type "world" from beginning

### Scenario 3: Similar words
- Display: "typing"
- New text: "typed"
- Action:
  1. Backspace "typing" → "typ" (random amount)
  2. Pause
  3. Clear to empty
  4. Type "typed" from beginning

## Common Pitfalls to Avoid
1. Don't clear displayText when props change
2. Don't reset the animation state unnecessarily
3. Make sure backspace animation is visible
4. Don't type over existing text - clear it first
5. Maintain proper timing for realistic effect