/**
 * AI Generation Operations - POST /ai/generate/*
 *
 * Example generation, facts, and word forms.
 */

import type { AIResponse } from '@/types/api';
import { api } from '../core';

export const generate = {
    // Generate examples - POST /ai/generate/examples
    async examples(
        word: string,
        definitionIndex: number,
        definitionText?: string,
        count?: number
    ): Promise<{
        word: string;
        definition_index: number;
        examples: Array<{ sentence: string; regenerable: boolean }>;
        confidence: number;
    }> {
        const response = await api.post(`/lookup/${word}/regenerate-examples`, {
            definition_index: definitionIndex,
            definition_text: definitionText,
            count: count || 2,
        });
        return response.data;
    },

    // Generate facts - POST /ai/generate/facts
    async facts(
        word: string,
        definition?: string
    ): Promise<{
        word: string;
        facts: Array<{ text: string; category: string; confidence: number }>;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                facts: Array<{
                    text: string;
                    category: string;
                    confidence: number;
                }>;
                confidence: number;
            }>
        >('/ai/generate/facts', {
            word,
            definition,
        });

        return {
            word,
            facts: response.data.result.facts || [],
            confidence: response.data.result.confidence || 0,
        };
    },

    // Generate word forms - POST /ai/generate/word-forms
    async wordForms(
        word: string,
        partOfSpeech?: string
    ): Promise<{
        word: string;
        forms: Record<string, string>;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                forms: Record<string, string>;
                confidence: number;
            }>
        >('/ai/generate/word-forms', {
            word,
            part_of_speech: partOfSpeech,
        });

        return {
            word,
            forms: response.data.result.forms || {},
            confidence: response.data.result.confidence || 0,
        };
    },
};
