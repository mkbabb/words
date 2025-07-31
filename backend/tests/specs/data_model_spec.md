# Data Model Testing Specification

## Core MongoDB Collections (Beanie ODM)

### Primary Entities
- **Word** - Core word entity (`text`, `normalized`, `language`, `offensive_flag`)
- **Definition** - Individual meanings with linguistic metadata (`part_of_speech`, `text`, `sense_number`)  
- **Example** - Usage examples (`definition_id`, `text`, `type`, `model_info`)
- **Pronunciation** - Phonetic data (`word_id`, `phonetic`, `ipa`, `audio_file_ids`)
- **Fact** - Interesting word information (`word_id`, `content`, `category`)

### Synthesis & AI
- **SynthesizedDictionaryEntry** - AI-synthesized comprehensive entries
- **ProviderData** - Raw dictionary provider data with source tracking
- **ModelInfo** - AI generation metadata for traceability

### Learning System
- **WordList** - User lists with spaced repetition data
- **WordListItem** - Individual words with learning metadata
- **ReviewData** - SM-2 algorithm implementation for spaced repetition
- **LearningStats** - Aggregated learning analytics

### Media & Assets
- **AudioMedia** - Audio files with format/accent/quality metadata
- **ImageMedia** - Images with alt text and accessibility data
- Binary data handling with proper Content-Type management

### Relationships & Extensions
- **WordRelationship** - Synonym/antonym/related word connections
- **PhrasalExpression** - Phrasal verbs, idioms, multi-word expressions
- **Etymology** - Word origin and historical development

## Embedded Models (Not Stored Separately)
- **BaseMetadata** - Common CRUD fields (`created_at`, `updated_at`, `version`)
- **WordForm** - Inflections (plural, past, comparative)
- **GrammarPattern** - Syntactic constructions
- **Collocation** - Common word combinations with frequency
- **UsageNote** - Grammar guidance and warnings
- **MeaningCluster** - Semantic grouping for definitions

## API-Only Models (Pydantic)
- **AI Response Models** - 40+ specialized AI interaction models
- **Request/Response Wrappers** - ResourceResponse, ListResponse, BatchResponse  
- **Validation Models** - Error handling with field-level details
- **Pagination/Sorting** - Query parameter models

## Database Design Patterns
- **Foreign Keys** - Extensive use of `PydanticObjectId` for efficient MongoDB references
- **Embedding vs Referencing** - Lightweight data embedded, heavy/shared data referenced
- **Indexing Strategy** - Compound indexes on common query patterns
- **Optimistic Locking** - Version-based concurrency control
- **CRUD Timestamps** - Automatic creation/update tracking

## Enums & Constants
- **Language** - ISO codes (EN, FR, ES, DE, IT)
- **DictionaryProvider** - Data sources (WIKTIONARY, OXFORD, AI_FALLBACK)
- **MasteryLevel** - Learning progression (DEFAULT, BRONZE, SILVER, GOLD)
- **NotificationFrequency** - Delivery schedules for word-of-day

## Testing Requirements
- MongoDB collection initialization and cleanup
- Document validation and constraint testing
- Relationship integrity across collections
- Embedded model serialization/deserialization
- Index performance and query optimization
- Optimistic locking collision handling
- Beanie ODM integration with FastAPI