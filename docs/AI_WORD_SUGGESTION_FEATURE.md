# AI Word Suggestion Feature

## Overview
Natural language word discovery system that transforms descriptive queries into curated word recommendations with confidence and aesthetic metrics.

## Core Components

### 1. Query Detection & UI Transformation
- **Trigger**: Search input exceeding corpus match + character threshold (~20 chars)
- **Visual Changes**:
  - Vertical expansion with smooth transition
  - Subtle golden hue overlay
  - Top-left sparkle animation indicator
  - Enter key initiates AI query

### 2. Query Validation Pipeline
- **Length Check**: Max 200 characters
- **Content Validation**: Meta-prompt filtering for:
  - Word-seeking queries ("words that mean...")
  - Descriptive word requests
  - Example sentence fill-ins
- **Failure Response**: Red search bar + toast notification

### 3. AI Processing Architecture

#### Models
```python
class WordSuggestion(BaseModel):
    word: str
    confidence: float  # 0-1 relevance score
    efflorescence: float  # 0-1 beauty/encapsulation score
    reasoning: str  # Why this word fits
    example_usage: Optional[str]  # Query context with word

class WordSuggestionResponse(BaseModel):
    suggestions: List[WordSuggestion]
    query_type: str
    original_query: str
```

#### Endpoints
- `POST /api/ai/suggest-words`: Main suggestion endpoint
- `POST /api/ai/validate-query`: Query validation endpoint

### 4. Display Mode ("_w" Mode)
- **Activation**: Gold indicator on floridify icon
- **Layout**: Card-based display ranked by confidence → efflorescence
- **Interactions**:
  - Click: Perform lookup → transition to definition view
  - Hover: Display reasoning tooltip
  - Cycle: Smooth animation between dictionary modes
- **Deactivation**: Auto-dismiss on standard word search

## Implementation Phases

### Phase 1: Backend Foundation
1. Create Pydantic models
2. Develop prompts (word_suggestion.md, query_validation.md)
3. Implement AI connector functions
4. Add API endpoints with validation

### Phase 2: Frontend Search Enhancement
1. Detect long queries in SearchBar.vue
2. Implement expansion animation
3. Add golden hue and sparkle effects
4. Install and configure toast system

### Phase 3: Display Implementation
1. Create WordSuggestionDisplay.vue component
2. Implement card-based layout
3. Add hover reasoning tooltips
4. Integrate with existing mode cycling

### Phase 4: Integration & Polish
1. Connect all components
2. Add smooth transitions
3. Test edge cases
4. Performance optimization

## Technical Specifications

### Backend
- **AI Model**: GPT-4 for nuanced word understanding
- **Caching**: Redis for suggestion results
- **Rate Limiting**: 10 queries/minute per user

### Frontend
- **Animation**: Framer Motion or CSS transitions
- **State Management**: Pinia store for suggestion state
- **Component Architecture**: Composable Vue 3.5 components

### Prompt Engineering
- **Word Suggestion**: Focus on semantic matching, cultural relevance, and lexical beauty
- **Validation**: Strict pattern matching for word-seeking queries

## Success Metrics
- Query → Results: <2s response time
- Relevance: >80% user satisfaction with suggestions
- UI: Smooth 60fps animations
- Error Rate: <5% invalid query submissions

## Development Iterations

### Iteration 1: Core Infrastructure
- Models, prompts, basic endpoints
- SearchBar detection logic

### Iteration 2: UI Implementation
- Complete visual transformations
- Basic suggestion display

### Iteration 3: Polish & Interactions
- Animations, tooltips, transitions
- Error handling refinement

### Iteration 4: Testing & Optimization
- API testing suite
- Browser MCP validation
- Performance tuning