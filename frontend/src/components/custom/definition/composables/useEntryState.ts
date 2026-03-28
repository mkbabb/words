import { computed } from 'vue';
import { useContentStore } from '@/stores';

/**
 * Derives the merged entry state from streaming + complete data,
 * plus isEmpty, isStreaming, and thesaurusData.
 */
export function useEntryState(activeSourceTab: { value: string }) {
    const contentStore = useContentStore();

    const entry = computed(() => {
        if (contentStore.definitionError?.hasError) {
            return null;
        }

        if (contentStore.isStreamingData && contentStore.partialEntry) {
            return {
                word:
                    contentStore.partialEntry.word ||
                    contentStore.currentEntry?.word,
                id: contentStore.partialEntry.id || contentStore.currentEntry?.id,
                last_updated:
                    contentStore.partialEntry.last_updated ||
                    contentStore.currentEntry?.last_updated,
                model_info:
                    contentStore.partialEntry.model_info ||
                    contentStore.currentEntry?.model_info,
                pronunciation:
                    contentStore.partialEntry.pronunciation ||
                    contentStore.currentEntry?.pronunciation,
                languages:
                    contentStore.partialEntry.languages ||
                    contentStore.currentEntry?.languages ||
                    [],
                etymology:
                    contentStore.partialEntry.etymology ||
                    contentStore.currentEntry?.etymology,
                images: [
                    ...(contentStore.partialEntry.images || []),
                    ...(contentStore.currentEntry?.images || []),
                ],
                definitions:
                    contentStore.partialEntry.definitions ||
                    contentStore.currentEntry?.definitions ||
                    [],
                source_entries: contentStore.currentEntry?.source_entries || [],
                _isStreaming: true,
                _streamingProgress: 0,
            } as any;
        }

        return contentStore.currentEntry
            ? ({
                  ...contentStore.currentEntry,
                  _isStreaming: false,
              } as any)
            : null;
    });

    const isStreaming = computed(() => contentStore.isStreamingData);

    const isEmpty = computed(
        () =>
            entry.value &&
            (!entry.value.definitions || entry.value.definitions.length === 0),
    );

    // Thesaurus data with provider synonym extraction
    const thesaurusData = computed(() => {
        const currentSource = activeSourceTab.value;

        if (currentSource && currentSource !== 'synthesis' && entry.value) {
            const providerSynonyms = extractProviderSynonyms(entry.value, currentSource);
            if (providerSynonyms.length > 0) {
                return {
                    word: entry.value.word,
                    synonyms: providerSynonyms,
                    confidence: 0.7,
                };
            }
        }

        const data = contentStore.currentThesaurus;
        if (data) {
            return {
                word: data.word,
                synonyms: [...data.synonyms],
                confidence: data.confidence,
            };
        }

        if (entry.value?.definitions) {
            const synonyms = (entry.value.definitions as any[])
                .flatMap((d: any) => d.synonyms || [])
                .filter(
                    (s: string, i: number, arr: string[]) => arr.indexOf(s) === i,
                )
                .map((word: string) => ({ word, score: 0.8 }));
            if (synonyms.length > 0) {
                return { word: entry.value.word, synonyms, confidence: 0.7 };
            }
        }

        return null;
    });

    return {
        entry,
        isStreaming,
        isEmpty,
        thesaurusData,
    };
}

function extractProviderSynonyms(entryData: any, provider: string) {
    const synonymSet = new Set<string>();

    if (entryData.definitions) {
        for (const def of entryData.definitions) {
            if (!def.providers_data) continue;
            const providerEntries = Array.isArray(def.providers_data)
                ? def.providers_data
                : [def.providers_data];

            for (const pd of providerEntries) {
                if (pd.provider !== provider) continue;
                if (pd.definitions) {
                    for (const pDef of pd.definitions) {
                        if (pDef.synonyms) {
                            for (const s of pDef.synonyms) {
                                synonymSet.add(s);
                            }
                        }
                    }
                }
            }
        }
    }

    return Array.from(synonymSet).map((word) => ({ word, score: 1.0 }));
}
