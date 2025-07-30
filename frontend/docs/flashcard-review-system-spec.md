# Flashcard Review System Specification

## Overview

A beautiful, responsive flashcard review system implementing the Anki spaced repetition algorithm (SuperMemo SM-2 with Anki modifications) for optimal vocabulary learning and retention.

## Design Principles

- **KISS (Keep It Simple, Stupid)**: Clean, intuitive interface focusing on the learning experience
- **Beautiful UI**: Consistent with our design language using shadcn/ui components
- **Mobile-First**: Touch-friendly interface that works seamlessly across devices
- **Performance**: Smooth animations and responsive interactions
- **Accessibility**: Full keyboard navigation and screen reader support

## Core Features

### 1. Review Interface

#### Card Layout
```
┌─────────────────────────────────┐
│  Progress: [████████░░] 80%     │
│  Remaining: 12 cards            │
├─────────────────────────────────┤
│                                 │
│           WORD                  │
│         [Reveal]                │
│                                 │
│    (After reveal: Definition,   │
│     examples, pronunciation)    │
│                                 │
├─────────────────────────────────┤
│  [Again] [Hard] [Good] [Easy]   │
│        1m    10m    1d   4d     │
└─────────────────────────────────┘
```

#### Review Modes
1. **Recognition Mode**: Word → Definition
2. **Recall Mode**: Definition → Word
3. **Mixed Mode**: Alternates between recognition and recall
4. **Pronunciation Mode**: Audio → Word/Definition

### 2. Spaced Repetition Algorithm

#### Modified Anki Algorithm
- **Initial interval**: 1 day for new cards
- **Ease factor**: Starting at 2.5, modified based on performance
- **Interval multiplier**: Configurable (default 1.0)
- **Learning steps**: [1m, 10m] for new/failed cards
- **Graduating interval**: 1 day
- **Maximum interval**: 365 days (configurable)

#### Quality Responses
1. **Again (0)**: Complete failure, restart learning
2. **Hard (1)**: Difficult recall, reduce ease factor
3. **Good (2)**: Correct recall, normal progression
4. **Easy (3)**: Very easy, increase interval and ease

### 3. Card States

```typescript
enum CardState {
  NEW = 'new',           // Never reviewed
  LEARNING = 'learning', // In learning phase
  REVIEW = 'review',     // In normal review cycle
  RELEARNING = 'relearning' // Failed review, back to learning
}

// ReviewData is stored within WordListItem in the backend
interface ReviewData {
  state: CardState;
  due: Date;
  interval: number;      // Days until next review
  easeFactor: number;    // Difficulty multiplier (1.3-2.5)
  repetitions: number;   // Successful review count
  lapses: number;       // Failed review count
  lastReview?: Date;
  learningStep: number; // Current position in learning steps
}

// Note: Review data is persisted as part of WordListItem model,
// not as separate card entities. Each word in a wordlist maintains
// its own review state specific to that list.
```

### 4. UI Components

#### FlashcardReviewModal.vue
Main modal container for the review session:
- Full-screen overlay with blur background
- Escape to exit with confirmation
- Progress tracking and statistics
- Session summary on completion

#### FlashcardDisplay.vue
Core flashcard component:
- Smooth flip animations using CSS transforms
- Content area with responsive typography
- Audio playback controls for pronunciation
- Image support for visual learning

#### ReviewButtons.vue
Response quality buttons:
- Color-coded difficulty levels
- Keyboard shortcuts (1-4 or A,S,D,F)
- Haptic feedback on mobile
- Next review time preview

#### ProgressIndicator.vue
Session progress tracking:
- Linear progress bar with smooth animations
- Card count (remaining/total)
- Session statistics (new, learning, review)
- Time remaining estimate

### 5. Animation System

#### Card Transitions
```css
.card-flip-enter-active, .card-flip-leave-active {
  transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.card-flip-enter-from {
  transform: rotateY(-90deg) scale(0.8);
}

.card-flip-leave-to {
  transform: rotateY(90deg) scale(0.8);
}
```

#### Button Feedback
- Scale animation on press (0.95x)
- Color transition for selection
- Ripple effect for touch feedback

### 6. Keyboard Shortcuts

- **Space**: Reveal card / Show answer
- **1-4**: Quality responses (Again, Hard, Good, Easy)
- **A,S,D,F**: Alternative quality responses
- **Enter**: Good response (most common)
- **Backspace**: Undo last review
- **Escape**: Exit review session

### 7. Mobile Optimizations

#### Touch Gestures
- **Tap**: Reveal card
- **Swipe left**: Hard response
- **Swipe right**: Good response
- **Swipe up**: Easy response
- **Swipe down**: Again response

#### Responsive Design
- Large touch targets (minimum 44px)
- Readable typography across screen sizes
- Appropriate spacing for thumb navigation

### 8. Data Flow

```typescript
// Review session flow using API endpoints
const startReviewSession = async (wordlistId: string, options: ReviewOptions) => {
  const response = await api.post(`/wordlists/${wordlistId}/review-sessions`, options);
  return response.data;
};

const getNextCard = async (wordlistId: string, sessionId: string) => {
  const response = await api.get(`/wordlists/${wordlistId}/review-sessions/${sessionId}/next-card`);
  return response.data;
};

const submitResponse = async (wordlistId: string, sessionId: string, quality: Quality, word: string) => {
  const response = await api.post(`/wordlists/${wordlistId}/review-sessions/${sessionId}/response`, {
    word,
    quality,
    responseTime: calculateResponseTime()
  });
  return response.data; // Returns updated review data
};

// Client-side algorithm reference (server handles actual calculation)
const calculateNextReview = (current: ReviewData, quality: Quality): ReviewData => {
  // Algorithm is implemented server-side for consistency
  // This is just for reference/documentation
  switch (current.state) {
    case CardState.NEW:
    case CardState.LEARNING:
      return handleLearningCard(current, quality);
    case CardState.REVIEW:
      return handleReviewCard(current, quality);
  }
};
```

### 9. Settings & Customization

#### Review Options
```typescript
interface ReviewOptions {
  mode: 'recognition' | 'recall' | 'mixed' | 'pronunciation';
  maxCards: number;
  timeLimit?: number; // in minutes
  showTimer: boolean;
  playAudio: boolean;
  newCardLimit: number;
  reviewCardLimit: number;
}
```

#### Algorithm Parameters
```typescript
interface AlgorithmSettings {
  easeFactor: {
    initial: number; // 2.5
    minimum: number; // 1.3
    maximum: number; // 2.5
  };
  intervals: {
    learning: number[]; // [1, 10] minutes
    graduating: number; // 1 day
    maximum: number; // 365 days
  };
  modifiers: {
    hard: number; // 1.2
    easy: number; // 1.3
    intervalMultiplier: number; // 1.0
  };
}
```

### 10. Statistics & Analytics

#### Session Statistics
- Cards reviewed
- Accuracy rate
- Average response time
- Session duration
- Cards mastered this session

#### Long-term Analytics
- Learning velocity
- Retention rate over time
- Difficult words identification
- Progress visualization

### 11. Implementation Phases

#### Phase 1: Core Review System
- [ ] Basic flashcard display
- [ ] SM-2 algorithm implementation
- [ ] Response quality buttons
- [ ] Progress tracking

#### Phase 2: Enhanced UX
- [ ] Smooth animations
- [ ] Keyboard shortcuts
- [ ] Mobile touch gestures
- [ ] Audio support

#### Phase 3: Advanced Features
- [ ] Multiple review modes
- [ ] Custom settings
- [ ] Statistics dashboard
- [ ] Undo functionality

#### Phase 4: Polish & Optimization
- [ ] Performance optimization
- [ ] Accessibility improvements
- [ ] Advanced analytics
- [ ] Export/import functionality

### 12. Technical Considerations

#### Performance
- Virtual scrolling for large card sets
- Lazy loading of audio/images
- Efficient DOM updates
- Background preloading

#### Accessibility
- ARIA labels for all interactive elements
- Focus management during modal navigation
- Screen reader announcements for progress
- High contrast mode support

#### Testing
- Unit tests for algorithm implementation
- Integration tests for review flow
- Visual regression tests for animations
- Performance benchmarks

### 13. Integration Points

#### With Existing System
- Wordlist selection and filtering
- Progress synchronization with main app
- Settings persistence
- Theme consistency

#### API Endpoints

Following the existing API patterns in the codebase, all endpoints are centered around wordlists:

```typescript
// Review Session Management
POST   /api/v1/wordlists/{wordlist_id}/review-sessions
GET    /api/v1/wordlists/{wordlist_id}/review-sessions/current
GET    /api/v1/wordlists/{wordlist_id}/review-sessions/{session_id}
PUT    /api/v1/wordlists/{wordlist_id}/review-sessions/{session_id}/complete

// Card Reviews (within sessions)
GET    /api/v1/wordlists/{wordlist_id}/review-sessions/{session_id}/next-card
POST   /api/v1/wordlists/{wordlist_id}/review-sessions/{session_id}/response
POST   /api/v1/wordlists/{wordlist_id}/review-sessions/{session_id}/undo

// Due Cards & Statistics
GET    /api/v1/wordlists/{wordlist_id}/due-cards
GET    /api/v1/wordlists/{wordlist_id}/review-stats
GET    /api/v1/wordlists/{wordlist_id}/words/{word}/review-data

// Review Settings
GET    /api/v1/wordlists/{wordlist_id}/review-settings
PUT    /api/v1/wordlists/{wordlist_id}/review-settings
```

##### Request/Response Examples

**Start Review Session**
```typescript
POST /api/v1/wordlists/{wordlist_id}/review-sessions
{
  "mode": "mixed",
  "maxCards": 50,
  "newCardLimit": 10,
  "includeOverdue": true
}

Response:
{
  "id": "session-123",
  "wordlistId": "wordlist-456",
  "totalCards": 25,
  "completedCards": 0,
  "startedAt": "2025-01-29T10:00:00Z",
  "settings": { ... }
}
```

**Submit Review Response**
```typescript
POST /api/v1/wordlists/{wordlist_id}/review-sessions/{session_id}/response
{
  "word": "effulgent",
  "quality": 2,  // 0=Again, 1=Hard, 2=Good, 3=Easy
  "responseTime": 3.5
}

Response:
{
  "nextReview": "2025-01-30T10:00:00Z",
  "interval": 1,
  "easeFactor": 2.4,
  "repetitions": 1
}
```

This specification provides a comprehensive foundation for implementing a world-class flashcard review system that enhances vocabulary learning through proven spaced repetition techniques while maintaining our commitment to beautiful, intuitive design.