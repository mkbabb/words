# Anki Export

## Flashcard Generation

AI creates academically rigorous flashcards from synthesized dictionary definitions. Two card types designed for GRE-level vocabulary assessment.

### Fill-in-the-Blank Cards

**Format**: Context sentence with strategic word removal
**Difficulty**: GRE-level semantic understanding
**Purpose**: Tests comprehension in realistic usage contexts

**Example**:
> The diplomat's _______ allowed him to navigate complex international negotiations.
> Answer: acumen

### Multiple Choice Cards

**Format**: Definition-based questions with four options
**Distractors**: Semantically related but incorrect choices
**Purpose**: Tests precise definitional knowledge

**Example**:
> What does "perspicacious" mean?
> A) Having keen insight and discernment
> B) Stubbornly persistent
> C) Overly talkative
> D) Easily deceived

## Deck Management

**File Format**: .apkg files compatible with Anki desktop and mobile
**Styling**: Claude-inspired CSS for professional presentation
**Organization**: Word lists exported as themed decks with metadata

### Export Process

1. **Word Selection**: Process word list through lookup pipeline
2. **Card Generation**: AI creates both card types per word
3. **Deck Assembly**: genanki library builds .apkg file
4. **Export**: Save to specified location or update existing deck

## CLI Integration

**Command**: `floridify anki export <word-list-name> [output-path]`
**Options**: Card type selection, deck naming, styling themes
**Batch Processing**: Full word list pipeline integration

## Styling System

**Claude Theme**: Professional typography with subtle gradients
**Responsive**: Works across Anki platforms
**Typography**: Optimized for readability and academic presentation

## Data Flow

```
Word List → Lookup Pipeline → AI Card Generation → Deck Assembly → .apkg Export
```

Each word generates two flashcards with synthesized definitions as answer content, maintaining consistency with the dictionary lookup system.