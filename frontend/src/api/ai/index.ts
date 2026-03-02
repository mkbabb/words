/**
 * AI API Module - Barrel Export
 *
 * Assembles the `aiApi` object from sub-modules. The `@/api/ai` or `./ai`
 * import path resolves to this directory index automatically.
 */

import { synthesize } from './synthesize';
import { generate } from './generate';
import { assess } from './assess';
import {
    validateQuery,
    generateUsageNotes,
    synthesizeEntry,
    suggestWords,
    suggestWordsStream,
} from './suggestions';

export const aiApi = {
    synthesize,
    generate,
    assess,
    validateQuery,
    generateUsageNotes,
    synthesizeEntry,
    suggestWords,
    suggestWordsStream,
};
