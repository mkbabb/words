# Floridify API Redesign Plan

## Overview
Complete redesign of the dictionary API to provide comprehensive CRUD operations, component regeneration, and modern RESTful patterns.

## Development Cycles

### Cycle 1: Foundation (Core CRUD)
- **Goal**: Establish base CRUD operations for all data models
- **Focus**: Words, Definitions, Facts, Examples, Pronunciations
- **Pattern**: RESTful resource-based endpoints with consistent response shapes

### Cycle 2: Component Regeneration  
- **Goal**: Enable granular regeneration of synthesized components
- **Focus**: Individual component refresh without full re-synthesis
- **Pattern**: Action-based endpoints for regeneration operations

### Cycle 3: Performance & Optimization
- **Goal**: Implement caching, batching, and query optimization
- **Focus**: Response time, database query efficiency, caching strategy
- **Pattern**: ETags, conditional requests, batch operations

### Cycle 4: Frontend Integration
- **Goal**: Document and prepare frontend migration path
- **Focus**: Breaking changes, migration guide, type updates
- **Pattern**: Versioned API with clear deprecation path

## Design Principles
1. **Resource-Oriented**: Clear resource hierarchy (words → definitions → components)
2. **Stateless**: All state in database, no session dependencies
3. **Cacheable**: Aggressive caching with proper invalidation
4. **Versioned**: API version in URL path for backward compatibility
5. **Consistent**: Uniform response shapes and error handling
6. **Performant**: Optimized queries, minimal object creation

## API Structure Preview
```
/api/v2/
├── /words
│   ├── GET    /         # List/search words
│   ├── POST   /         # Create word
│   ├── GET    /{id}     # Get word details
│   ├── PUT    /{id}     # Update word
│   ├── DELETE /{id}     # Delete word
│   └── /batch           # Batch operations
├── /definitions
│   ├── GET    /         # List definitions
│   ├── POST   /         # Create definition
│   ├── GET    /{id}     # Get definition
│   ├── PUT    /{id}     # Update definition
│   ├── DELETE /{id}     # Delete definition
│   └── /regenerate      # Regeneration endpoints
├── /synthesis
│   ├── POST   /         # New synthesis
│   ├── GET    /{id}     # Get synthesized entry
│   └── /components      # Component operations
└── /search
    ├── /multi-method    # Cascading search
    └── /semantic        # Vector search
```

## Next Steps
1. Research existing codebase structure
2. Analyze current API patterns and pain points
3. Design detailed endpoint specifications
4. Implement incrementally with tests