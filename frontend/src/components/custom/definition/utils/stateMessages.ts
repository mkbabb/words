/**
 * Helper functions for error and empty state display messages.
 */

export const getErrorTitle = (errorType: string): string => {
    switch (errorType) {
        case 'network':
            return 'Connection Error';
        case 'not-found':
            return 'Word Not Found';
        case 'server':
            return 'Server Error';
        case 'ai-failed':
            return 'AI Processing Failed';
        case 'empty':
            return 'No Definitions Found';
        default:
            return 'Something Went Wrong';
    }
};

export const getEmptyTitle = (originalWord?: string): string => {
    return originalWord
        ? `No definitions found for "${originalWord}"`
        : 'No definitions found';
};

export const getEmptyMessage = (): string => {
    return 'This word might not exist in our dictionary, or it could be a specialized term. Try searching for a similar word or check your spelling.';
};
