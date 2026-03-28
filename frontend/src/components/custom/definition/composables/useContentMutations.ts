import { definitionsApi, examplesApi, entriesApi } from '@/api'
import { useContentStore } from '@/stores/content/content'
import type { Definition, SynthesizedDictionaryEntry } from '@/types'

/**
 * Composable for content mutation operations that involve API calls.
 *
 * Extracts API-calling logic that previously lived in the content store
 * (via the lookup content state). Stores should only hold pure state
 * setters; network operations belong here.
 */
export function useContentMutations() {
  const contentStore = useContentStore()

  /**
   * Update a definition via the API and apply the result to the store.
   */
  const updateDefinition = async (definitionId: string, updates: Partial<Definition>) => {
    const response = await definitionsApi.updateDefinition(definitionId, updates)

    contentStore.applyDefinitionUpdate(definitionId, updates)

    return response
  }

  /**
   * Update an example's text via the API and refresh store state.
   */
  const updateExample = async (_definitionId: string, exampleId: string, newText: string) => {
    const response = await examplesApi.updateExample(exampleId, { text: newText })

    // Trigger a shallow refresh so the UI picks up changes
    contentStore.touchCurrentEntry()

    return response
  }

  /**
   * Regenerate a specific component of a definition via the API.
   */
  const regenerateDefinitionComponent = async (
    definitionId: string,
    component: 'definition' | 'examples' | 'usage_notes'
  ) => {
    const response = await definitionsApi.regenerateComponents(definitionId, component)

    contentStore.applyDefinitionComponentRegeneration(
      definitionId,
      component,
      response as unknown as Record<string, unknown>
    )

    return response
  }

  /**
   * Regenerate examples for a definition at the given index.
   */
  const regenerateExamples = async (definitionIndex: number) => {
    const entry = contentStore.currentEntry
    if (!entry?.definitions?.[definitionIndex]) return

    // Prevent concurrent operations
    if (contentStore.regeneratingDefinitionIndex !== null) return

    const definition = entry.definitions[definitionIndex]
    const definitionId = definition.id

    contentStore.setRegeneratingDefinitionIndex(definitionIndex)

    try {
      const response = await definitionsApi.regenerateComponents(definitionId, 'examples')

      contentStore.applyExamplesRegeneration(definitionIndex, response)

      return response
    } finally {
      contentStore.setRegeneratingDefinitionIndex(null)
    }
  }

  /**
   * Refresh entry images from the API.
   */
  const refreshEntryImages = async () => {
    const entry = contentStore.currentEntry
    if (!entry) return

    const entryId = (entry as any).id || entry.word
    const response = await entriesApi.refreshEntryImages(entryId)

    contentStore.setCurrentEntry({
      ...entry,
      ...response
    } as unknown as SynthesizedDictionaryEntry)

    return response
  }

  return {
    updateDefinition,
    updateExample,
    regenerateDefinitionComponent,
    regenerateExamples,
    refreshEntryImages,
  }
}
