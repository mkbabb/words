# Wordlist Performance Optimization Plan

## Current Performance Issues
- Upload takes ~98 seconds for 1,771 words
- Sequential processing with individual DB operations
- String/ObjectId conversions on every query
- No progress feedback to client
- Inefficient ID storage strategy

## Optimization Phases

### Phase 1: Batch Operations (Immediate Impact)
1. **Batch Word Lookup**: Use `find({"normalized": {"$in": normalized_list}})` instead of individual lookups
2. **Bulk Word Creation**: Use `insert_many()` for new words
3. **Estimated Performance Gain**: 90% reduction in DB round trips

### Phase 2: ID Type Optimization
1. **Change `word_id: str` to `word_id: PydanticObjectId`** in WordListItem
2. **Remove all string/ObjectId conversions**
3. **Update serialization to handle ObjectIds properly**
4. **Estimated Performance Gain**: 10-20% query improvement

### Phase 3: Streaming Progress Updates
1. **Implement SSE (Server-Sent Events)** for real-time progress
2. **Update frontend to show progress modal**
3. **Track: parsing, word lookup, word creation, list creation**
4. **User Experience**: Real-time feedback instead of 98-second wait

### Phase 4: Additional Optimizations
1. **Index `normalized` field** for faster lookups
2. **Connection pooling optimization**
3. **Parallel processing where possible**
4. **Cache frequently accessed words**

## Implementation Order
1. Batch operations (biggest impact, least breaking)
2. Progress streaming (improves UX immediately)
3. ID type changes (requires migration)
4. Additional optimizations

## Expected Results
- Upload time: 98s → ~5-10s
- Better user experience with progress feedback
- More efficient database usage
- Cleaner, more maintainable code