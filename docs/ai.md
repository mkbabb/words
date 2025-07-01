# AI Integration - Floridify

## Core Components

### 1. Definition Synthesis
Aggregates definitions from multiple providers at word-type-meaning level into coherent, unified definitions.

### 2. Example Generation  
Generates contemporary, contextually relevant example sentences for word usage.

### 3. Pronunciation Generation
Creates phonetic and IPA pronunciations for words.

### 4. AI Fallback Provider
Generates complete dictionary entries for unknown words as last resort.

## Architecture

- **OpenAI Integration**: Modern async API with structured outputs
- **Model Detection**: Auto-detect reasoning vs standard models
- **Caching**: Full API response and result caching with MongoDB
- **Templates**: Jinja2-based prompt templates in `ai/prompts/`
- **Persistence**: Beanie ODM for automatic serialization

## Key Classes

- `OpenAIConnector`: Core API client with caching
- `DefinitionSynthesizer`: Entry synthesis from providers
- `PromptTemplateManager`: Template rendering engine
- `SynthesizedDictionaryEntry`: Final output model

## Configuration

Uses `auth/config.toml`:
- API keys and model selection
- Temperature (auto-disabled for reasoning models)
- Rate limiting and caching TTL

## Usage

```python
from floridify.ai import create_ai_system

connector, synthesizer = create_ai_system()
entry = await synthesizer.synthesize_entry(word, providers)
```