# Word of the Day System - Initial Architecture Plan

## System Overview

A sophisticated word-of-the-day generation system that combines AI-powered word selection, user preference learning, and historical data ingestion to deliver personalized, beautiful, and meaningful words.

## Core Components

### 1. Data Ingestion Pipeline
- **Gmail Scraper**: Extract historical word-of-the-day emails using googleapiutils2
- **Word List Seeder**: Leverage existing /backend/data/words.txt
- **Corpus Integration**: Connect to existing language corpus system

### 2. Word Generation Engine
- **Primary Generator**: OpenAI GPT-4 API (existing integration)
- **Custom Model**: Fine-tuned model for specialized word generation
  - Focus: Beauty, efflorescence, semantic density
  - Input: User preferences, historical words, thematic constraints
  - Output: Ranked word candidates with confidence scores

### 3. User Preference System
- **Quiz Module**: Interactive preference discovery
  - Literary preferences (Shakespeare, Woolf, etc.)
  - Domain interests (botanical, scientific, philosophical)
  - Aesthetic preferences (florid, minimalist, archaic)
- **Preference Vector**: Mathematical representation of user tastes
- **Adaptive Learning**: Refine preferences based on engagement

### 4. Scheduling & Delivery
- **Batch Generation**: Create N days of content in advance
- **Quantum Flexibility**: Support arbitrary delivery intervals
- **Queue Management**: FIFO with preference-based reordering

### 5. Quality Assurance
- **Uniqueness Filter**: Prevent duplicate selections
- **Beauty Metrics**: Phonetic analysis, semantic richness scoring
- **Utility Assessment**: Practical applicability measurement

## Technical Architecture

### Backend Components
```
/backend/src/floridify/
├── wotd/                       # Word of the Day module
│   ├── models/                 # Data models
│   │   ├── word_entry.py       # Core word representation
│   │   ├── preferences.py      # User preference modeling
│   │   └── schedule.py         # Delivery scheduling
│   ├── generators/             # Word generation engines
│   │   ├── openai_gen.py       # GPT-4 integration
│   │   ├── custom_model.py     # Fine-tuned model
│   │   └── hybrid.py           # Combined approach
│   ├── scrapers/               # Data collection
│   │   ├── gmail_scraper.py    # Email ingestion
│   │   └── corpus_bridge.py    # Connect to existing corpus
│   ├── analyzers/              # Word quality assessment
│   │   ├── beauty_scorer.py    # Aesthetic evaluation
│   │   ├── uniqueness.py       # Duplicate prevention
│   │   └── utility.py          # Practical value
│   └── api/                    # API endpoints
│       ├── generation.py       # Word generation endpoints
│       ├── preferences.py      # User preference management
│       └── delivery.py         # Scheduling and sending
```

### Frontend Components
```
/frontend/src/
├── components/wotd/            # Word of the Day UI
│   ├── QuizFlow.vue            # Preference quiz
│   ├── WordDisplay.vue         # Beautiful word presentation
│   └── ScheduleManager.vue     # Delivery configuration
├── stores/wotd/                # State management
│   ├── preferences.ts          # User preferences
│   ├── queue.ts                # Word queue
│   └── history.ts              # Historical tracking
```

## Data Models

### Word Entry
```python
class WOTDEntry:
    word: str
    definitions: List[Definition]  # Leverage existing
    etymology: str
    usage_examples: List[str]
    beauty_score: float
    utility_score: float
    themes: List[str]
    corpus_sources: List[str]
    generation_metadata: dict
```

### User Preferences
```python
class UserPreferences:
    literary_sources: List[str]     # ["shakespeare", "woolf"]
    domains: List[str]               # ["botanical", "philosophy"]
    aesthetic_style: str             # "florid" | "minimalist" | "archaic"
    complexity_preference: float     # 0.0 to 1.0
    frequency_preference: str        # "rare" | "uncommon" | "balanced"
    preference_vector: np.ndarray    # Mathematical representation
```

## Integration Points

1. **Existing AI Connector**: Extend current OpenAI integration
2. **MongoDB Storage**: Leverage existing Beanie ODM
3. **Search Infrastructure**: Use FAISS for similarity matching
4. **Corpus System**: Connect to language_loader and corpus manager
5. **Definition Repository**: Reuse definition_repository.py

## Development Priorities

### Phase 1: Foundation
1. Gmail scraper implementation
2. Basic preference system
3. OpenAI-based generation

### Phase 2: Enhancement
1. Custom model fine-tuning
2. Advanced preference learning
3. Beauty/utility scoring

### Phase 3: Polish
1. Sophisticated scheduling
2. UI/UX refinement
3. Performance optimization

## Key Algorithms

### Word Selection Algorithm
```
1. Generate candidate pool (100-500 words)
2. Apply user preference filter
3. Score for beauty and utility
4. Check uniqueness against history
5. Rank by composite score
6. Select top N for queue
```

### Preference Learning
```
1. Initialize from quiz responses
2. Track engagement metrics
3. Update preference vector using gradient descent
4. Periodically retrain custom model
```

## Research Questions

1. **Model Selection**: Which base model for fine-tuning? (GPT-2, BERT, custom transformer)
2. **Training Data**: How to structure fine-tuning dataset from scraped emails?
3. **Beauty Metrics**: Objective measures for word aesthetics?
4. **Duplicate Prevention**: Semantic similarity threshold?
5. **Corpus Integration**: Optimal way to leverage existing search infrastructure?

## Next Steps

1. Deploy research agents to analyze codebase
2. Investigate Gmail API authentication flow
3. Research modern fine-tuning libraries (Hugging Face, etc.)
4. Examine existing word data structure
5. Map integration points with current system