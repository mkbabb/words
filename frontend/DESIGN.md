# Words Design Language

> Extends [glass-ui DESIGN.md](../../glass-ui/DESIGN.md)

## Token Overrides

Fraunces serif stack for literary character. Warm color palette with mastery-level semantic colors: card states (new/learning/review/mastered), review quality grades, chart gradients for progress visualization.

Texture system with four bases (clean, aged, handmade, kraft) at three intensities (subtle, medium, strong)—applied via `background-image` layering. Pre-computed `color-mix()` values for performance in virtualized list rendering.

## Local Utilities

- `dialog-surface` — Dialog backdrop with texture + glass
- `popover-surface` — Popover panel styling (texture-aware)
- `card-surface` — Base card with texture integration
- `word-card` — Performance-optimized card: no `backdrop-blur` to keep virtualized grids smooth; uses opaque backgrounds with pre-mixed colors instead

## Migration Tasks

- [ ] Replace WordLookupPopover manual positioning with glass-ui Popover (gains reka-ui flip/overflow)
- [ ] Add `interactive-item` hover pattern to WordListRow
- [ ] Extract mode templates from DefinitionDisplay.vue (7-9 levels) into DictionaryMode.vue, ThesaurusMode.vue
- [ ] Consider HoverCard for word definition preview on list hover
