/**
 * AI Assessment Operations - POST /ai/assess/*
 *
 * Frequency, CEFR, register, domain, collocations, grammar patterns,
 * and regional variants assessment.
 */

import type { AIResponse } from '@/types/api';
import { api } from '../core';

export const assess = {
    // Assess frequency band - POST /ai/assess/frequency
    async frequency(word: string): Promise<{
        word: string;
        frequency_band: number;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                frequency_band: number;
                confidence: number;
            }>
        >('/ai/assess/frequency', { word });

        return {
            word,
            frequency_band: response.data.result.frequency_band,
            confidence: response.data.result.confidence || 0,
        };
    },

    // Assess CEFR level - POST /ai/assess/cefr
    async cefr(
        word: string,
        definition?: string
    ): Promise<{
        word: string;
        cefr_level: string;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                cefr_level: string;
                confidence: number;
            }>
        >('/ai/assess/cefr', {
            word,
            definition,
        });

        return {
            word,
            cefr_level: response.data.result.cefr_level,
            confidence: response.data.result.confidence || 0,
        };
    },

    // Assess language register - POST /ai/assess/register
    async register(
        word: string,
        definition?: string
    ): Promise<{
        word: string;
        register: string;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                register: string;
                confidence: number;
            }>
        >('/ai/assess/register', {
            word,
            definition,
        });

        return {
            word,
            register: response.data.result.register,
            confidence: response.data.result.confidence || 0,
        };
    },

    // Assess domain - POST /ai/assess/domain
    async domain(
        word: string,
        definition?: string
    ): Promise<{
        word: string;
        domain: string;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                domain: string;
                confidence: number;
            }>
        >('/ai/assess/domain', {
            word,
            definition,
        });

        return {
            word,
            domain: response.data.result.domain,
            confidence: response.data.result.confidence || 0,
        };
    },

    // Assess collocations - POST /ai/assess/collocations
    async collocations(
        word: string,
        definition?: string
    ): Promise<{
        word: string;
        collocations: Array<{ phrase: string; frequency: number }>;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                collocations: Array<{ phrase: string; frequency: number }>;
                confidence: number;
            }>
        >('/ai/assess/collocations', {
            word,
            definition,
        });

        return {
            word,
            collocations: response.data.result.collocations || [],
            confidence: response.data.result.confidence || 0,
        };
    },

    // Assess grammar patterns - POST /ai/assess/grammar-patterns
    async grammarPatterns(
        word: string,
        definition?: string
    ): Promise<{
        word: string;
        patterns: Array<{ pattern: string; examples: string[] }>;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                patterns: Array<{ pattern: string; examples: string[] }>;
                confidence: number;
            }>
        >('/ai/assess/grammar-patterns', {
            word,
            definition,
        });

        return {
            word,
            patterns: response.data.result.patterns || [],
            confidence: response.data.result.confidence || 0,
        };
    },

    // Assess regional variants - POST /ai/assess/regional-variants
    async regionalVariants(word: string): Promise<{
        word: string;
        variants: Array<{ region: string; variant: string; usage: string }>;
        confidence: number;
    }> {
        const response = await api.post<
            AIResponse<{
                variants: Array<{
                    region: string;
                    variant: string;
                    usage: string;
                }>;
                confidence: number;
            }>
        >('/ai/assess/regional-variants', { word });

        return {
            word,
            variants: response.data.result.variants || [],
            confidence: response.data.result.confidence || 0,
        };
    },
};
