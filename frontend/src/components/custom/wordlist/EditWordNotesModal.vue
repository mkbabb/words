<template>
  <Dialog :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>Edit Notes</DialogTitle>
        <DialogDescription>
          Update notes for "{{ word?.text }}"
        </DialogDescription>
      </DialogHeader>
      
      <div class="space-y-4 py-4">
        <div class="space-y-2">
          <label for="notes" class="text-sm font-medium">Notes</label>
          <Textarea
            id="notes"
            v-model="localNotes"
            placeholder="Add your notes about this word..."
            class="min-h-[100px] resize-none"
            @keydown.meta.enter="handleSave"
            @keydown.ctrl.enter="handleSave"
          />
          <p class="text-xs text-muted-foreground">
            Press {{ isMac ? 'Cmd' : 'Ctrl' }} + Enter to save
          </p>
        </div>
      </div>
      
      <DialogFooter>
        <Button 
          variant="outline" 
          @click="handleCancel"
        >
          Cancel
        </Button>
        <Button 
          @click="handleSave"
          :disabled="!hasChanges"
        >
          Save Notes
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import type { WordListItem } from '@/types'

interface Props {
  modelValue: boolean
  word: WordListItem | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'save', word: WordListItem, notes: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const localNotes = ref('')
const originalNotes = ref('')

const isMac = computed(() => {
  return typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0
})

const hasChanges = computed(() => {
  return localNotes.value !== originalNotes.value
})

// Watch for word changes to initialize notes
watch(() => props.word, (newWord) => {
  if (newWord) {
    originalNotes.value = newWord.notes || ''
    localNotes.value = newWord.notes || ''
  }
}, { immediate: true })

// Reset when modal closes
watch(() => props.modelValue, (isOpen) => {
  if (!isOpen) {
    // Reset to original when closing without saving
    localNotes.value = originalNotes.value
  }
})

const handleSave = () => {
  if (props.word && hasChanges.value) {
    emit('save', props.word, localNotes.value)
    originalNotes.value = localNotes.value
  }
  emit('update:modelValue', false)
}

const handleCancel = () => {
  localNotes.value = originalNotes.value
  emit('update:modelValue', false)
}
</script>