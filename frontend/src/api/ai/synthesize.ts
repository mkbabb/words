/**
 * AI Synthesis Operations - POST /ai/synthesize/*
 *
 * Synonyms, antonyms, and pronunciation synthesis.
 */

import type { AIResponse, DictionaryEntryResponse } from '@/types/api';
import type { ThesaurusEntry } from '@/types';
import { api, transformError } from '../core';
import { logger } from '@/utils/logger';

export const synthesize = {
    // Generate synonyms - POST /ai/synthesize/synonyms
    async synonyms(word: string): Promise<ThesaurusEntry> {
        try {
            // Get word context from lookup
            const dictionaryEntryResponse =
                await api.get<DictionaryEntryResponse>(
                    `/lookup/${encodeURIComponent(word)}`
                );

            // Safely extract entry data - handle both direct response and wrapped envelope shapes
            const entryData = dictionaryEntryResponse.data;
            if (!entryData) {
                throw new Error(`No data returned from lookup for "${word}"`);
            }

            // Extract definitions, handling potential response shape variations
            const definitions =
                entryData.definitions ?? (entryData as any).entry?.definitions;
            if (
                !definitions ||
                !Array.isArray(definitions) ||
                definitions.length === 0
            ) {
                throw new Error(`No definitions found for "${word}"`);
            }

            const firstDefinition = definitions[0];

            // Call AI synthesis endpoint with consistent parameter structure
            const response = await api.post<
                AIResponse<{
                    synonyms: Array<{ word: string; score: number }>;
                    confidence: number;
                }>
            >('/ai/synthesize/synonyms', {
                word,
                definition: firstDefinition.text ?? '',
                part_of_speech: firstDefinition.part_of_speech ?? '',
                existing_synonyms: firstDefinition.synonyms ?? [],
                count: 10,
            });

            // Safely extract AI result
            const result = response.data?.result;

            // Transform response to frontend format
            return {
                word,
                synonyms: result?.synonyms ?? [],
                confidence: result?.confidence ?? 0,
            };
        } catch (error) {
            logger.error('Error fetching synonyms:', error);
            throw transformError(error);
        }
    },

    // Generate antonyms - POST /ai/synthesize/antonyms
    async antonyms(
        word: string,
        definition: string,
        partOfSpeech?: string
    ): Promise<{
        word: string;
        antonyms: Array<{ word: string; score: number }>;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                antonyms: Array<{ word: string; score: number }>;
                confidence: number;
            }>
        >('/ai/synthesize/antonyms', {
            word,
            definition,
            part_of_speech: partOfSpeech,
            count: 10,
        });

        const result = response.data?.result;
        return {
            word,
            antonyms: result?.antonyms ?? [],
            confidence: result?.confidence ?? 0,
        };
    },

    // Generate pronunciation - POST /ai/synthesize/pronunciation
    async pronunciation(word: string): Promise<{
        word: string;
        phonetic: string;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                phonetic: string;
                confidence: number;
            }>
        >('/ai/synthesize/pronunciation', { word });

        return {
            word,
            phonetic: response.data.result.phonetic,
            confidence: response.data.result.confidence || 0,
        };
    },
};
