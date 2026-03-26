<template>
    <div v-if="showForm" class="space-y-4">
        <!-- Upload Mode Toggle -->
        <div class="space-y-2">
            <label class="text-sm font-medium">Upload Mode</label>
            <div class="flex rounded-lg border bg-muted/30 p-1">
                <Button
                    @click="$emit('update:uploadMode', 'new')"
                    :variant="uploadMode === 'new' ? 'default' : 'ghost'"
                    size="sm"
                    class="flex-1 text-sm"
                >
                    Create New
                </Button>
                <Button
                    @click="$emit('update:uploadMode', 'existing')"
                    :variant="uploadMode === 'existing' ? 'default' : 'ghost'"
                    size="sm"
                    class="flex-1 text-sm"
                >
                    Add to Existing
                </Button>
            </div>
        </div>

        <!-- Existing Wordlist Selection -->
        <div v-if="uploadMode === 'existing'" class="space-y-2">
            <label class="text-sm font-medium">Select Wordlist</label>
            <DropdownMenu>
                <DropdownMenuTrigger as-child>
                    <Button
                        variant="outline"
                        class="w-full justify-between"
                        :disabled="isLoadingWordlist"
                    >
                        <span>
                            {{
                                selectedWordlist
                                    ? `${selectedWordlist.name} (${formatCount(selectedWordlist.unique_words)} words)`
                                    : 'Select a wordlist...'
                            }}
                        </span>
                        <ChevronDown class="h-4 w-4 opacity-50" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent class="w-full">
                    <DropdownMenuItem
                        v-for="wordlist in wordlists"
                        :key="wordlist.id"
                        @click="$emit('update:selectedWordlistId', wordlist.id)"
                        class="cursor-pointer"
                    >
                        <div class="flex flex-col items-start">
                            <span class="font-medium">{{ wordlist.name }}</span>
                            <span class="text-xs text-muted-foreground">
                                {{ formatCount(wordlist.unique_words) }} words
                            </span>
                        </div>
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>

        <!-- New Wordlist Form -->
        <div v-if="uploadMode === 'new'" class="space-y-3">
            <!-- Name with Slug Generation -->
            <div class="space-y-2">
                <label class="text-sm font-medium">Name</label>
                <div class="relative">
                    <Input
                        :model-value="newWordlistName"
                        @update:model-value="
                            (v: string | number) =>
                                $emit('update:newWordlistName', String(v))
                        "
                        placeholder="Wordlist name (optional)..."
                        class="w-full pr-10"
                        @input="$emit('name-input')"
                    />
                    <div class="absolute top-1/2 right-2 -translate-y-1/2">
                        <RefreshButton
                            :loading="slugGenerating"
                            :disabled="isUploading"
                            variant="ghost"
                            title="Generate random name"
                            @click="$emit('generate-slug')"
                        />
                    </div>
                </div>
                <p v-if="isSlugGenerated" class="text-xs text-muted-foreground">
                    Random name generated - you can edit it or generate a new
                    one
                </p>
            </div>
            <!-- Description -->
            <div class="space-y-2">
                <label class="text-sm font-medium">Description</label>
                <Input
                    :model-value="newWordlistDescription"
                    @update:model-value="
                        (v: string | number) =>
                            $emit('update:newWordlistDescription', String(v))
                    "
                    placeholder="Description (optional)..."
                    class="w-full"
                />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ChevronDown } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import RefreshButton from '@/components/custom/common/RefreshButton.vue';
import type { WordList } from '@/types';
import { formatCount } from './utils/formatting';

defineProps<{
    showForm: boolean;
    uploadMode: 'new' | 'existing';
    wordlists: WordList[];
    selectedWordlist: WordList | undefined;
    isLoadingWordlist: boolean;
    newWordlistName: string;
    newWordlistDescription: string;
    slugGenerating: boolean;
    isUploading: boolean;
    isSlugGenerated: boolean;
}>();

defineEmits<{
    'update:uploadMode': [value: 'new' | 'existing'];
    'update:selectedWordlistId': [value: string];
    'update:newWordlistName': [value: string];
    'update:newWordlistDescription': [value: string];
    'name-input': [];
    'generate-slug': [];
}>();
</script>
