/**
 * AI Query Detection and Word Count Extraction Utilities
 * 
 * Functions for detecting AI mode queries and extracting word counts
 */

/**
 * Checks if a query should trigger AI mode based on:
 * - Query is clearly a question or request (contains question words)
 * - Query has many words (more than 3) suggesting natural language
 * - Query explicitly asks for suggestions/words
 * @param queryText The search query text
 * @returns True if query should trigger AI mode
 */
export function shouldTriggerAIMode(queryText: string): boolean {
    const lowerQuery = queryText.toLowerCase().trim();
    
    // Don't trigger for short phrases that are likely dictionary lookups
    const wordCount = lowerQuery.split(/\s+/).length;
    if (wordCount <= 2 && lowerQuery.length < 20) {
        return false;
    }
    
    // Check for question indicators
    const questionWords = ['what', 'which', 'how', 'why', 'when', 'where', 'who', 'give me', 'show me', 'find me', 'suggest', 'list'];
    const hasQuestionWord = questionWords.some(word => lowerQuery.includes(word));
    
    // Check for AI request patterns
    const aiPatterns = ['words that', 'words for', 'words about', 'words like', 'synonyms', 'similar to', 'related to'];
    const hasAIPattern = aiPatterns.some(pattern => lowerQuery.includes(pattern));
    
    // Check for number requests (e.g., "10 words about...")
    const hasNumberRequest = /\b\d+\s+words?\b/.test(lowerQuery);
    
    return hasQuestionWord || hasAIPattern || hasNumberRequest || wordCount > 2;
}

/**
 * Checks if a query contains the "_w" AI mode pattern
 * @param queryText The search query text
 * @returns True if query contains "_w" pattern
 */
export function hasAIModePattern(queryText: string): boolean {
    return queryText.includes('_w');
}

/**
 * Extracts word count from a natural language query
 * Supports numeric digits, written numbers, and common phrases
 * @param queryText The query text to extract count from
 * @returns The extracted word count (1-25, default 12)
 */
export function extractWordCount(queryText: string): number {
    // Regular expression to match various number patterns:
    // - Written numbers (one to twenty-five)
    // - Numeric digits (1, 10, 25)
    // - Common phrases like "a few" (3), "several" (5), "many" (10)
    
    // First try to match numeric digits
    const numericMatch = queryText.match(/\b(\d+)\b/);
    if (numericMatch) {
        const count = parseInt(numericMatch[1], 10);
        // Cap at 25 as requested (backend caps at 20)
        return Math.min(Math.max(count, 1), 25);
    }
    
    // Then try written numbers (ordered by length to prioritize compound numbers)
    const writtenNumbers: Record<string, number> = {
        'twenty-five': 25, 'twenty five': 25,
        'twenty-four': 24, 'twenty four': 24,
        'twenty-three': 23, 'twenty three': 23,
        'twenty-two': 22, 'twenty two': 22,
        'twenty-one': 21, 'twenty one': 21,
        'twenty': 20, 'nineteen': 19, 'eighteen': 18, 'seventeen': 17,
        'sixteen': 16, 'fifteen': 15, 'fourteen': 14, 'thirteen': 13,
        'twelve': 12, 'eleven': 11, 'ten': 10, 'nine': 9, 'eight': 8,
        'seven': 7, 'six': 6, 'five': 5, 'four': 4, 'three': 3, 'two': 2, 'one': 1
    };
    
    const lowerQuery = queryText.toLowerCase();
    // Sort by length descending to match longer patterns first
    const sortedEntries = Object.entries(writtenNumbers).sort((a, b) => b[0].length - a[0].length);
    
    for (const [word, value] of sortedEntries) {
        if (lowerQuery.includes(word)) {
            return value;
        }
    }
    
    // Check for common phrases
    if (lowerQuery.includes('a few') || lowerQuery.includes('few')) {
        return 3;
    }
    if (lowerQuery.includes('several')) {
        return 5;
    }
    if (lowerQuery.includes('many') || lowerQuery.includes('a lot') || lowerQuery.includes('lots')) {
        return 10;
    }
    if (lowerQuery.includes('a couple') || lowerQuery.includes('couple')) {
        return 2;
    }
    
    // Default to 12 if no count specified
    return 12;
}