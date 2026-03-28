<template>
  <div v-if="wordlists.length > 0" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
    <ThemedCard
      v-for="wl in wordlists"
      :key="wl.id"
      :variant="cardVariant(wl)"
      @click="$emit('select', wl)"
      :class="[
        'group relative overflow-hidden rounded-2xl p-5 text-left shadow-sm h-[11rem] cursor-pointer',
        'transition-[transform,box-shadow] duration-200 ease-apple-default hover:shadow-md hover:-translate-y-px active:scale-[0.98] focus-ring',
      ]"
      :texture-enabled="false"
      hide-star
      :border-shimmer="false"
    >
      <!-- Three-dot menu (lazy) -->
      <div class="absolute right-3 top-3 z-content opacity-0 transition-opacity duration-200 group-hover:opacity-100"
           @mouseenter="activeMenu = wl.id">
        <DropdownMenu v-if="activeMenu === wl.id">
          <DropdownMenuTrigger as-child>
            <Button
              variant="ghost"
              size="icon"
              class="h-7 w-7 text-muted-foreground/70 hover:text-foreground"
              @click.stop
            >
              <MoreVertical class="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" @click.stop>
            <div v-if="wl.tags && wl.tags.length > 0" class="flex flex-wrap gap-1 px-2 py-1.5">
              <span
                v-for="tag in wl.tags"
                :key="tag"
                class="rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground tracking-wide"
              >
                {{ tag }}
              </span>
            </div>
            <DropdownMenuSeparator v-if="wl.tags && wl.tags.length > 0" />
            <DropdownMenuItem @click.stop="$emit('edit', wl)">
              <Pencil class="mr-2 h-4 w-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem @click.stop="$emit('manage-tags', wl)">
              <Tag class="mr-2 h-4 w-4" /> Manage Tags
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem class="text-destructive" @click.stop="$emit('delete', wl)">
              <Trash2 class="mr-2 h-4 w-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        <Button
          v-else
          variant="ghost"
          size="icon"
          class="h-7 w-7 text-muted-foreground/70 hover:text-foreground"
          @click.stop="activeMenu = wl.id"
        >
          <MoreVertical class="h-4 w-4" />
        </Button>
      </div>

      <!-- Content -->
      <div class="relative">
        <h3 class="text-heading font-serif font-semibold leading-snug truncate">{{ wl.name }}</h3>

        <p
          v-if="wl.description"
          class="mt-1 line-clamp-2 text-small text-muted-foreground/80 leading-relaxed"
        >
          {{ wl.description }}
        </p>

        <div class="mt-3 flex items-center gap-2.5 text-caption text-muted-foreground/60">
          <span class="flex items-center gap-1">
            <span class="tabular-nums font-medium text-foreground/70">{{ formatCount(wl.unique_words ?? wl.total_words ?? 0) }}</span>
            words
          </span>
          <span class="text-border">&middot;</span>
          <span v-if="lastAccessedLabel(wl)">{{ lastAccessedLabel(wl) }}</span>
          <span v-else-if="wl.created_at">{{ formatRelativeTime(wl.created_at) }}</span>
        </div>

        <MasteryBar
          :mastered-count="masteryCount(wl, 'mastered')"
          :familiar-count="masteryCount(wl, 'familiar')"
          :learning-count="masteryCount(wl, 'learning')"
          :total-words="wl.unique_words ?? wl.total_words ?? 0"
        />
      </div>

      <!-- Hover arrow -->
      <div
        class="absolute right-4 top-1/2 -translate-y-1/2 translate-x-2 opacity-0 transition-[opacity,transform]
               duration-200 group-hover:translate-x-0 group-hover:opacity-40"
      >
        <ChevronRight class="h-4 w-4" />
      </div>
    </ThemedCard>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ChevronRight, MoreVertical, Pencil, Tag, Trash2 } from 'lucide-vue-next';
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, Button } from '@mkbabb/glass-ui';
import { ThemedCard } from '@/components/custom/card';
import MasteryBar from './MasteryBar.vue';
import type { WordList } from '@/types';
import type { CardVariant } from '@/types';
import { formatCount } from './utils/formatting';

interface Props {
  wordlists: WordList[];
}

interface Emits {
  (e: 'select', wl: WordList): void;
  (e: 'delete', wl: WordList): void;
  (e: 'edit', wl: WordList): void;
  (e: 'manage-tags', wl: WordList): void;
}

defineProps<Props>();
defineEmits<Emits>();

const activeMenu = ref<string | null>(null);

function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

function lastAccessedLabel(wl: WordList): string {
  if (!wl.last_accessed) return '';
  return formatRelativeTime(wl.last_accessed);
}

function getMasteryCounts(wl: WordList) {
  if (wl.words && wl.words.length > 0) {
    const counts = { bronze: 0, silver: 0, gold: 0, default: 0 };
    for (const w of wl.words) {
      const level = (w as any).mastery_level || 'default';
      counts[level as keyof typeof counts] = (counts[level as keyof typeof counts] || 0) + 1;
    }
    return counts;
  }
  const stats = wl.learning_stats;
  if (!stats) return { bronze: 0, silver: 0, gold: 0, default: 0 };
  const mastered = stats.words_mastered ?? 0;
  const total = wl.unique_words ?? wl.total_words ?? 0;
  return {
    gold: mastered,
    silver: 0,
    bronze: Math.max(0, total - mastered),
    default: 0,
  };
}

function masteryCount(wl: WordList, level: 'mastered' | 'familiar' | 'learning'): number {
  const counts = getMasteryCounts(wl);
  if (level === 'mastered') return counts.gold;
  if (level === 'familiar') return counts.silver;
  return counts.bronze + counts.default;
}

function cardVariant(wl: WordList): CardVariant {
  const counts = getMasteryCounts(wl);
  const total = wl.unique_words ?? wl.total_words ?? 0;
  if (total === 0) return 'default';
  const goldPct = counts.gold / total;
  if (goldPct > 0.8) return 'gold';
  if (goldPct > 0.5) return 'silver';
  if (counts.bronze + counts.default > 0) return 'bronze';
  return 'default';
}
</script>
