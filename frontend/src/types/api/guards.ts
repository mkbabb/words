/**
 * Backend API Type Definitions - Type Guards
 *
 * Runtime type guard functions for API model validation.
 */

import type { Word, Definition, Example, MeaningCluster } from './models';

export function isWord(obj: any): obj is Word {
    return (
        obj &&
        typeof obj.text === 'string' &&
        typeof obj.normalized === 'string'
    );
}

export function isDefinition(obj: any): obj is Definition {
    return (
        obj &&
        typeof obj.word_id === 'string' &&
        typeof obj.part_of_speech === 'string'
    );
}

export function isExample(obj: any): obj is Example {
    return (
        obj &&
        typeof obj.text === 'string' &&
        (obj.type === 'generated' || obj.type === 'literature')
    );
}

export function isMeaningCluster(obj: any): obj is MeaningCluster {
    return obj && typeof obj.id === 'string' && typeof obj.slug === 'string' && typeof obj.name === 'string';
}
