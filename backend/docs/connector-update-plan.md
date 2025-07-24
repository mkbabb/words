# Connector Update Plan

## Overview
Update all dictionary connectors to extract data for the enhanced model fields.

## Phase 1: Base Connector Enhancement

### 1.1 Update base.py
- Add methods for extracting new fields
- Create field mapping utilities
- Add default values for unsupported fields

## Phase 2: Wiktionary Connector

### 2.1 New Extraction Methods
```python
def _extract_usage_notes(section) -> list[str]
def _extract_register_labels(text) -> str | None  
def _extract_regional_variants(text) -> str | None
def _extract_collocations(section) -> list[str]
def _extract_antonyms(section) -> list[str]
def _extract_word_forms(section) -> list[WordForm]
```

### 2.2 Template Parsing
- Parse {{context|informal|en}} → register="informal"
- Parse {{qualifier|US}} → region="US"
- Extract from "Usage notes" sections
- Parse "Derived terms" for collocations

## Phase 3: Oxford Connector

### 3.1 API Field Mapping
```python
# Map Oxford API fields to our model:
sense.registers → definition.register
sense.domains → definition.domain
sense.regions → definition.region
lexicalEntry.grammaticalFeatures → definition.grammar_patterns
sense.notes → definition.usage_notes
```

### 3.2 CEFR Level Extraction
- Check if Oxford provides CEFR data
- Fall back to AI assessment if not

## Phase 4: Apple Dictionary Connector

### 4.1 Limited Extraction
- Parse definition text for usage indicators
- Extract basic grammatical information
- Mark fields for AI enrichment

## Phase 5: Dictionary.com Connector

### 5.1 Full Implementation
- Implement web scraping or API integration
- Extract difficulty levels if available
- Parse usage labels and regional variants

## Phase 6: Provider Data Aggregation

### 6.1 Create aggregation utilities
```python
def merge_provider_fields(providers: list[ProviderData]) -> dict
def select_best_value(values: list[Any], field_type: str) -> Any
```

## Testing Strategy

1. Create test fixtures with known data
2. Verify extraction accuracy
3. Handle missing data gracefully
4. Performance test parsing operations