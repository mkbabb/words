# User Preference Quiz System Design

## Overview

A sophisticated preference discovery system that creates personalized word-of-the-day experiences through interactive quizzes, implicit learning, and continuous adaptation.

## Core Philosophy

The quiz system follows a "show, don't tell" approach - instead of asking abstract questions, we present words and learn from user interactions.

## Quiz Architecture

### Phase 1: Initial Discovery Quiz

#### Literary Source Preferences
```typescript
interface LiteraryPreferenceQuestion {
  type: 'word_comparison';
  prompt: 'Which word resonates more with you?';
  options: [
    {
      word: 'forsooth',
      sample: 'Forsooth, the stars do shine upon thy visage',
      source: 'shakespeare',
      hidden_tags: ['archaic', 'dramatic', 'formal']
    },
    {
      word: 'ineffable',
      sample: 'The ineffable quality of the light in the drawing room',
      source: 'woolf',
      hidden_tags: ['modernist', 'introspective', 'sophisticated']
    }
  ];
}
```

#### Aesthetic Style Discovery
```typescript
interface AestheticQuestion {
  type: 'word_rating';
  prompt: 'Rate how much you enjoy these words:';
  words: [
    { text: 'mellifluous', style: 'florid', phonetic_beauty: 0.92 },
    { text: 'stark', style: 'minimalist', phonetic_beauty: 0.45 },
    { text: 'efflorescence', style: 'ornate', phonetic_beauty: 0.88 },
    { text: 'cut', style: 'simple', phonetic_beauty: 0.30 }
  ];
}
```

#### Domain Interest Mapping
```typescript
interface DomainQuestion {
  type: 'word_categorization';
  prompt: 'Select all words that intrigue you:';
  words: [
    { text: 'photosynthesis', domain: 'botanical', complexity: 0.7 },
    { text: 'epistemology', domain: 'philosophical', complexity: 0.9 },
    { text: 'crescendo', domain: 'musical', complexity: 0.5 },
    { text: 'quasar', domain: 'astronomical', complexity: 0.8 },
    { text: 'algorithm', domain: 'computational', complexity: 0.6 }
  ];
}
```

### Phase 2: Preference Vector Generation

#### Mathematical Representation
```python
import numpy as np
from sklearn.preprocessing import StandardScaler

class PreferenceVector:
    """Multi-dimensional preference representation."""
    
    def __init__(self):
        # 64-dimensional embedding space
        self.dimensions = {
            # Literary dimensions (0-15)
            'shakespeare_affinity': 0,
            'woolf_affinity': 1,
            'contemporary_affinity': 2,
            'classical_affinity': 3,
            
            # Aesthetic dimensions (16-31)
            'floridity': 16,
            'minimalism': 17,
            'archaism': 18,
            'modernism': 19,
            'phonetic_beauty': 20,
            'semantic_density': 21,
            
            # Domain dimensions (32-47)
            'botanical': 32,
            'philosophical': 33,
            'scientific': 34,
            'artistic': 35,
            'emotional': 36,
            'technical': 37,
            
            # Complexity dimensions (48-63)
            'word_length_preference': 48,
            'syllable_complexity': 49,
            'etymology_depth': 50,
            'frequency_preference': 51,
            'novelty_seeking': 52
        }
        
        self.vector = np.zeros(64)
        self.confidence = np.ones(64) * 0.5  # Confidence per dimension
    
    def update_from_quiz(self, quiz_responses):
        """Update vector based on quiz responses."""
        for response in quiz_responses:
            self._process_response(response)
        
        # Normalize vector
        self.vector = StandardScaler().fit_transform(
            self.vector.reshape(-1, 1)
        ).flatten()
    
    def _process_response(self, response):
        """Process individual quiz response."""
        if response.type == 'word_comparison':
            chosen = response.chosen_option
            rejected = response.rejected_option
            
            # Increase chosen attributes
            for tag in chosen.hidden_tags:
                dim = self.dimensions.get(tag)
                if dim is not None:
                    self.vector[dim] += 0.3
                    self.confidence[dim] = min(1.0, self.confidence[dim] + 0.1)
            
            # Decrease rejected attributes
            for tag in rejected.hidden_tags:
                dim = self.dimensions.get(tag)
                if dim is not None:
                    self.vector[dim] -= 0.1
```

### Phase 3: Adaptive Learning System

#### Engagement Tracking
```python
class EngagementTracker:
    """Track user engagement with generated words."""
    
    def __init__(self):
        self.engagement_events = []
    
    def track_event(self, event_type: str, word: str, metadata: dict):
        """Track engagement events."""
        event = {
            'timestamp': datetime.now(),
            'type': event_type,  # 'view', 'click', 'save', 'share', 'skip'
            'word': word,
            'duration': metadata.get('duration', 0),
            'interaction_depth': self._calculate_depth(event_type),
            'metadata': metadata
        }
        self.engagement_events.append(event)
    
    def _calculate_depth(self, event_type: str) -> float:
        """Calculate engagement depth score."""
        depth_scores = {
            'skip': -1.0,
            'view': 0.1,
            'click': 0.3,
            'read_definition': 0.5,
            'save': 0.8,
            'share': 1.0,
            'use_in_sentence': 1.0
        }
        return depth_scores.get(event_type, 0)
    
    def calculate_word_score(self, word: str) -> float:
        """Calculate overall engagement score for a word."""
        word_events = [e for e in self.engagement_events if e['word'] == word]
        
        if not word_events:
            return 0.5  # Neutral score
        
        # Weighted sum of interactions
        total_score = sum(e['interaction_depth'] for e in word_events)
        
        # Time decay factor
        latest_event = max(word_events, key=lambda e: e['timestamp'])
        days_ago = (datetime.now() - latest_event['timestamp']).days
        decay_factor = 0.95 ** days_ago
        
        return min(1.0, max(0.0, (total_score * decay_factor) / len(word_events)))
```

#### Preference Evolution
```python
class PreferenceLearner:
    """Continuously learn and refine user preferences."""
    
    def __init__(self, initial_vector: PreferenceVector):
        self.preference_vector = initial_vector
        self.learning_rate = 0.01
        self.momentum = 0.9
        self.velocity = np.zeros_like(initial_vector.vector)
    
    def update_preferences(self, word: str, engagement_score: float):
        """Update preferences based on word engagement."""
        # Get word features
        word_features = self._extract_word_features(word)
        
        # Calculate gradient
        target_score = engagement_score
        predicted_score = self._predict_engagement(word_features)
        error = target_score - predicted_score
        
        # Update vector using momentum SGD
        gradient = error * word_features
        self.velocity = self.momentum * self.velocity + self.learning_rate * gradient
        self.preference_vector.vector += self.velocity
        
        # Update confidence
        self._update_confidence(word_features, abs(error))
    
    def _extract_word_features(self, word: str) -> np.ndarray:
        """Extract feature vector from word."""
        features = np.zeros(64)
        
        # Phonetic features
        features[20] = self._calculate_phonetic_beauty(word)
        
        # Length and complexity
        features[48] = len(word) / 20.0  # Normalized length
        features[49] = self._count_syllables(word) / 10.0
        
        # Domain detection (would use existing search infrastructure)
        detected_domains = self._detect_domains(word)
        for domain, score in detected_domains.items():
            if domain in self.preference_vector.dimensions:
                dim = self.preference_vector.dimensions[domain]
                features[dim] = score
        
        return features
```

## Frontend Implementation

### Vue 3 Quiz Component
```vue
<template>
  <div class="wotd-preference-quiz">
    <TransitionGroup name="question-transition" tag="div">
      <QuizQuestion
        v-for="(question, index) in currentQuestions"
        :key="question.id"
        :question="question"
        :progress="(index + 1) / totalQuestions"
        @answer="handleAnswer"
      />
    </TransitionGroup>
    
    <div v-if="quizComplete" class="quiz-results">
      <PreferenceProfile :profile="generatedProfile" />
      <Button @click="startPersonalization">
        Start My Word Journey
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useWOTDPreferences } from '@/stores/wotd/preferences';

const preferences = useWOTDPreferences();

// Adaptive quiz generation
const currentQuestions = computed(() => {
  return preferences.generateAdaptiveQuestions(
    previousAnswers.value,
    remainingQuestions.value
  );
});

const handleAnswer = async (answer: QuizAnswer) => {
  // Process answer
  await preferences.processAnswer(answer);
  
  // Update preference vector in real-time
  preferences.updateVector(answer);
  
  // Generate next question based on response
  if (preferences.needsMoreData()) {
    generateNextQuestion();
  } else {
    completeQuiz();
  }
};
</script>
```

### Pinia Store for Preferences
```typescript
export const useWOTDPreferences = defineStore('wotd-preferences', () => {
  // State
  const preferenceVector = ref<Float32Array>(new Float32Array(64));
  const confidence = ref<Float32Array>(new Float32Array(64).fill(0.5));
  const quizHistory = ref<QuizResponse[]>([]);
  
  // Computed
  const dominantPreferences = computed(() => {
    const indexed = Array.from(preferenceVector.value)
      .map((val, idx) => ({ dimension: idx, value: val, confidence: confidence.value[idx] }))
      .filter(item => item.confidence > 0.7)
      .sort((a, b) => b.value - a.value)
      .slice(0, 5);
    
    return indexed.map(item => getDimensionName(item.dimension));
  });
  
  const preferenceProfile = computed<UserPreferenceProfile>(() => ({
    literary: extractLiteraryProfile(preferenceVector.value),
    aesthetic: extractAestheticProfile(preferenceVector.value),
    domains: extractDomainProfile(preferenceVector.value),
    complexity: extractComplexityProfile(preferenceVector.value)
  }));
  
  // Actions
  const generateAdaptiveQuestions = (
    previousAnswers: QuizAnswer[],
    questionPool: Question[]
  ): Question[] => {
    // Use uncertainty sampling to select most informative questions
    const uncertainDimensions = findUncertainDimensions(confidence.value);
    
    return questionPool
      .filter(q => q.dimensions.some(d => uncertainDimensions.includes(d)))
      .sort((a, b) => calculateInformationGain(b) - calculateInformationGain(a))
      .slice(0, 3);
  };
  
  const updateVector = (answer: QuizAnswer) => {
    // Update preference vector based on answer
    const features = extractAnswerFeatures(answer);
    
    for (const [dimension, value] of features) {
      preferenceVector.value[dimension] += value * 0.1;
      confidence.value[dimension] = Math.min(1.0, confidence.value[dimension] + 0.05);
    }
    
    // Normalize vector
    normalizeVector(preferenceVector.value);
  };
  
  // Persistence
  return {
    preferenceVector,
    confidence,
    quizHistory,
    dominantPreferences,
    preferenceProfile,
    generateAdaptiveQuestions,
    updateVector,
    persist: {
      key: 'wotd-preferences',
      storage: localStorage,
      pick: ['preferenceVector', 'confidence', 'quizHistory']
    }
  };
});
```

## Quiz Flow and UX Design

### Progressive Disclosure
1. **Quick Start** (3 questions) - Basic preferences
2. **Deep Dive** (10 questions) - Detailed preferences
3. **Continuous Learning** - Ongoing refinement through usage

### Question Types

#### Binary Choice
- Fast, low cognitive load
- Good for initial preference discovery
- A/B testing word pairs

#### Rating Scale
- 5-star rating for individual words
- Captures preference intensity
- Allows neutral responses

#### Multi-Select
- Choose all that apply
- Good for domain discovery
- Reveals preference breadth

#### Semantic Differential
- Slider between opposites (Simple ← → Complex)
- Captures preference continuums
- Visual and intuitive

### Gamification Elements

#### Progress Tracking
```typescript
interface PreferenceJourney {
  level: number;  // 1-10
  xp: number;  // Experience points
  badges: Badge[];
  streaks: {
    daily: number;
    weekly: number;
  };
  milestones: Milestone[];
}
```

#### Achievements
- "Lexophile" - Complete initial quiz
- "Word Connoisseur" - Rate 100 words
- "Preference Pioneer" - Try all preference modes
- "Consistency Crown" - 30-day engagement streak

### Preference Modes

Users can switch between curated preference modes:

```typescript
const PREFERENCE_MODES = {
  'shakespeare': {
    name: 'Bardic Beauty',
    description: 'Elizabethan eloquence and dramatic flair',
    vector: shakespeareVector
  },
  'minimalist': {
    name: 'Essential Elegance',
    description: 'Simple, powerful, unforgettable',
    vector: minimalistVector
  },
  'scientific': {
    name: 'Precision & Wonder',
    description: 'Technical terms with fascinating origins',
    vector: scientificVector
  },
  'romantic': {
    name: 'Poetic Soul',
    description: 'Words that paint emotions and beauty',
    vector: romanticVector
  },
  'adventurous': {
    name: 'Linguistic Explorer',
    description: 'Rare gems from around the world',
    vector: adventurousVector
  }
};
```

## Integration with Word Generation

### Preference-Driven Prompting
```python
def generate_preference_prompt(user_vector: np.ndarray, count: int = 5) -> str:
    """Generate AI prompt based on user preferences."""
    
    # Decode top preferences
    top_dims = get_top_dimensions(user_vector, n=5)
    
    # Build prompt
    prompt_parts = []
    
    # Literary style
    if 'shakespeare_affinity' in top_dims:
        prompt_parts.append("in the style of Shakespeare")
    elif 'woolf_affinity' in top_dims:
        prompt_parts.append("with Virginia Woolf's introspective elegance")
    
    # Aesthetic preferences
    if 'floridity' in top_dims:
        prompt_parts.append("focusing on ornate, beautiful words")
    elif 'minimalism' in top_dims:
        prompt_parts.append("emphasizing simple, powerful words")
    
    # Domain preferences
    domains = [d for d in top_dims if d in DOMAIN_DIMENSIONS]
    if domains:
        prompt_parts.append(f"from {', '.join(domains)} domains")
    
    # Construct final prompt
    base = f"Generate {count} unique words"
    modifiers = " ".join(prompt_parts)
    
    return f"{base} {modifiers}. Each word should be memorable and meaningful."
```

### Preference Matching Score
```python
def calculate_word_preference_match(word: str, user_vector: np.ndarray) -> float:
    """Calculate how well a word matches user preferences."""
    
    # Extract word features
    word_vector = extract_word_vector(word)
    
    # Cosine similarity
    similarity = np.dot(word_vector, user_vector) / (
        np.linalg.norm(word_vector) * np.linalg.norm(user_vector)
    )
    
    # Apply confidence weighting
    weighted_similarity = similarity * np.mean(confidence_vector)
    
    return (weighted_similarity + 1) / 2  # Normalize to 0-1
```

## Analytics and Insights

### Preference Analytics Dashboard
```typescript
interface PreferenceAnalytics {
  // User preference evolution over time
  evolutionTimeline: {
    date: Date;
    vector: Float32Array;
    dominantPreferences: string[];
  }[];
  
  // Engagement metrics per preference dimension
  dimensionEngagement: Map<string, {
    averageScore: number;
    wordCount: number;
    trend: 'increasing' | 'stable' | 'decreasing';
  }>;
  
  // Successful word characteristics
  successfulWordPatterns: {
    averageLength: number;
    commonDomains: string[];
    phonemePatterns: string[];
  };
  
  // Prediction accuracy
  predictionMetrics: {
    accuracy: number;  // How well we predict engagement
    precision: number;
    recall: number;
  };
}
```

## Privacy and Data Handling

### Local-First Architecture
- All preference vectors stored locally
- No personal data sent to servers
- Anonymous aggregated insights only

### Export and Portability
```typescript
interface PreferenceExport {
  version: string;
  exportDate: Date;
  preferenceVector: number[];
  quizHistory: QuizResponse[];
  engagementHistory: EngagementEvent[];
  
  // Portable format
  toJSON(): string;
  toCSV(): string;
  toMarkdown(): string;
}
```

## Conclusion

This preference quiz system creates a sophisticated, adaptive learning environment that continuously improves word recommendations while maintaining user engagement through gamification and progressive disclosure. The mathematical foundation ensures accurate preference modeling while the UX design keeps the experience intuitive and enjoyable.