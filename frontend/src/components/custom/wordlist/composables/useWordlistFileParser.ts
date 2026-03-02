import { ref } from 'vue';
import { logger } from '@/utils/logger';

export interface ParsedWord {
    text: string;
    frequency: number;
    notes?: string;
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

    const parseTxtFile = (text: string): ParsedWord[] => {
        return text
            .split('\n')
            .map((line) => line.trim())
            .filter((line) => line && !line.startsWith('#'))
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
                    text: word,
                    frequency: parseInt(frequency) || 1,
                    notes: notes || undefined,
                };
            })
            .filter((item) => item.text);
    };

    const parseJsonFile = (text: string): ParsedWord[] => {
        const data = JSON.parse(text);

        if (Array.isArray(data)) {
            return data
                .map((item) => {
                    if (typeof item === 'string') {
                        return { text: item, frequency: 1 };
                    } else if (typeof item === 'object' && item.text) {
                        return {
                            text: item.text,
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
