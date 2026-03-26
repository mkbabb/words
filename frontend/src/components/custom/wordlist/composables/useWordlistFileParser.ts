import { ref } from 'vue';
import { logger } from '@/utils/logger';

export interface ParsedWord {
    text: string;
    frequency: number;
    notes?: string;
    resolvedText?: string;
}

interface UseWordlistFileParserOptions {
    onError: (message: string) => void;
}

/**
 * Handles file parsing logic for wordlist uploads.
 * Supports .txt, .csv, and .json file formats.
 */
export function useWordlistFileParser(options: UseWordlistFileParserOptions) {
    const { onError } = options;

    const uploadedFiles = ref<File[]>([]);
    const parsedWords = ref<ParsedWord[]>([]);

    const preserveTextFormat = (text: string): string => {
        return text
            .normalize('NFC')
            .replace(/[\u200b\u200c\u200d\ufeff]/g, '')
            .replace(/[“”]/g, '"')
            .replace(/[‘’]/g, "'")
            .replace(/[—–]/g, '-')
            .trim()
            .replace(/\s+/g, ' ');
    };

    const looksLikePhrase = (text: string): boolean => {
        const words = text.toLowerCase().split(/\s+/).filter(Boolean);
        if (words.length <= 1) return false;

        const phraseIndicators = new Set([
            'a', 'an', 'the', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'to',
            'and', 'or', 'but', 'from', 'as', 'is', 'are', 'was', 'were', 'be',
            'la', 'le', 'de', 'du', 'des', 'il', 'et', 'en', 'el', 'los', 'las',
            'y', 'o', 'del',
        ]);

        if (words.some((word) => phraseIndicators.has(word))) return true;

        const commonPhrases = new Set([
            'quid pro quo', 'carpe diem', 'et cetera', 'ad hoc', 'per se', 'vice versa',
            'status quo', 'modus operandi', 'alma mater', 'bona fide', 'de facto',
            'prima facie', 'pro bono', 'sine qua non', 'coup de grace', 'deja vu',
            'faux pas', "raison d'etre", 'au revoir', 'bon appetit', "c'est la vie",
            'joie de vivre',
        ]);

        if (commonPhrases.has(text.toLowerCase())) return true;
        return words.every((word) => word[0] === word[0]?.toUpperCase());
    };

    const isValidWord = (word: string): boolean => {
        if (!word) return false;
        if (word.length < 1 || word.length > 100) return false;
        if (!/[a-zA-Z\u00C0-\u017F\u0400-\u04FF]/.test(word)) return false;
        if (/^[\d\W\s]+$/.test(word)) return false;
        if (word.toLowerCase().includes('should be skipped')) return false;
        return true;
    };

    const extractWordsFromLine = (line: string): string[] => {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) return [];

        const numberedPatterns = [
            /^\d+[.)]\s*(.+)$/,
            /^\d+\.\s+(.+)$/,
            /^\d+\t(.+)$/,
            /^[a-zA-Z][.)]\s*(.+)$/,
        ];

        for (const pattern of numberedPatterns) {
            const match = trimmed.match(pattern);
            if (match?.[1]) {
                return [preserveTextFormat(match[1])];
            }
        }

        for (const bullet of ['-', '*', '•', '·', '○', '□', '▪', '▫', '►', '▸']) {
            if (trimmed.startsWith(bullet)) {
                const text = preserveTextFormat(trimmed.slice(bullet.length).trim());
                return text ? [text] : [];
            }
        }

        const normalized = preserveTextFormat(trimmed);
        if (!normalized) return [];

        if (normalized.includes(',') || normalized.includes(';')) {
            return normalized
                .split(/[,;]\s*/)
                .map((word) => preserveTextFormat(word))
                .filter(Boolean);
        }

        if (looksLikePhrase(normalized)) {
            return [normalized];
        }

        const parts = normalized.split(/\s+/).filter(Boolean);
        return parts.length > 1 ? parts : [normalized];
    };

    const parseTxtFile = (text: string): ParsedWord[] => {
        return text
            .split('\n')
            .flatMap((line) => extractWordsFromLine(line))
            .filter((word) => isValidWord(word))
            .map((word) => ({ text: word, frequency: 1 }));
    };

    const parseCsvFile = (text: string): ParsedWord[] => {
        const lines = text.split('\n').filter((line) => line.trim());
        const hasHeaders = lines[0]?.toLowerCase().includes('word');
        const dataLines = hasHeaders ? lines.slice(1) : lines;

        return dataLines
            .map((line) => {
                const [word, frequency = '1', notes = ''] = line
                    .split(',')
                    .map((s) => s.trim());
                return {
                    text: preserveTextFormat(word),
                    frequency: parseInt(frequency) || 1,
                    notes: notes || undefined,
                };
            })
            .filter((item) => isValidWord(item.text));
    };

    const parseJsonFile = (text: string): ParsedWord[] => {
        const data = JSON.parse(text);

        if (Array.isArray(data)) {
            return data
                .map((item) => {
                    if (typeof item === 'string') {
                        const text = preserveTextFormat(item);
                        return isValidWord(text)
                            ? { text, frequency: 1 }
                            : null;
                    } else if (typeof item === 'object' && item.text) {
                        const text = preserveTextFormat(item.text);
                        if (!isValidWord(text)) return null;
                        return {
                            text,
                            frequency: item.frequency || 1,
                            notes: item.notes,
                        };
                    }
                    return null;
                })
                .filter(Boolean) as ParsedWord[];
        }

        throw new Error('JSON must be an array');
    };

    const parseFile = async (file: File): Promise<void> => {
        try {
            const text = await file.text();
            const extension = file.name.toLowerCase().split('.').pop();

            let newWords: ParsedWord[] = [];

            switch (extension) {
                case 'txt':
                    newWords = parseTxtFile(text);
                    break;
                case 'csv':
                    newWords = parseCsvFile(text);
                    break;
                case 'json':
                    newWords = parseJsonFile(text);
                    break;
            }

            // Merge with existing parsed words, combining frequencies
            const wordMap = new Map<string, ParsedWord>();

            // Add existing words
            parsedWords.value.forEach((word) => {
                wordMap.set(word.text.toLowerCase(), word);
            });

            // Add new words
            newWords.forEach((word) => {
                const key = word.text.toLowerCase();
                if (wordMap.has(key)) {
                    const existing = wordMap.get(key)!;
                    existing.frequency += word.frequency;
                    if (word.notes && !existing.notes) {
                        existing.notes = word.notes;
                    }
                } else {
                    wordMap.set(key, word);
                }
            });

            parsedWords.value = Array.from(wordMap.values()).sort(
                (a, b) => b.frequency - a.frequency
            );
        } catch (err) {
            logger.error('File parsing error:', err);
            onError(`Failed to parse ${file.name}`);
        }
    };

    const addFiles = async (files: File[]) => {
        for (const file of files) {
            if (file.size > 10 * 1024 * 1024) {
                // 10MB limit
                onError(`File ${file.name} is too large (max 10MB)`);
                continue;
            }

            if (!file.name.match(/\.(txt|csv|json)$/i)) {
                onError(`File ${file.name} has unsupported format`);
                continue;
            }

            uploadedFiles.value.push(file);
            await parseFile(file);
        }
    };

    const removeFile = (fileToRemove: File) => {
        uploadedFiles.value = uploadedFiles.value.filter(
            (file) => file !== fileToRemove
        );

        // Re-parse remaining files
        parsedWords.value = [];
        uploadedFiles.value.forEach((file) => parseFile(file));
    };

    const reset = () => {
        uploadedFiles.value = [];
        parsedWords.value = [];
    };

    return {
        uploadedFiles,
        parsedWords,
        addFiles,
        removeFile,
        reset,
    };
}
