<template>
  <HoverCard :open-delay="200" :close-delay="100">
    <HoverCardTrigger as-child>
      <ThemedCard
        :variant="word.mastery_level"
        class="group relative cursor-pointer transition-all duration-500 ease-apple-spring hover:scale-[1.02] p-3"
        texture-enabled
        texture-type="clean"
        texture-intensity="subtle"
        @click="$emit('click', word)"
      >
        <!-- Main content -->
        <div>
          <!-- Header with word and status -->
          <div class="mb-3 flex items-center justify-between">
            <div class="min-w-0 flex-1">
              <h3 class="text-lg font-semibold truncate themed-title transition-colors group-hover:text-primary">
                {{ word.text }}
              </h3>
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{{ word.frequency }}x</span>
                <span>•</span>
                <span>{{ getMasteryLabel(word.mastery_level) }}</span>
                <span v-if="isDueForReview" class="ml-1 px-1.5 py-0.5 bg-primary/10 text-primary rounded-full">
                  Due
                </span>
              </div>
            </div>
            
            <!-- Temperature indicator -->
            <div class="flex items-center gap-2">
              <!-- Progress bar -->
              <div class="relative h-2 w-12 overflow-hidden rounded-full bg-muted">
                <div 
                  class="absolute inset-y-0 left-0 bg-gradient-to-r from-current to-current/70 transition-all duration-500"
                  :style="{ width: `${progressPercentage}%` }"
                />
              </div>
              <!-- Temperature -->
              <div class="text-sm">
                {{ word.temperature === 'hot' ? '🔥' : '❄️' }}
              </div>
            </div>
          </div>

          <!-- Quick stats -->
          <div class="flex justify-between text-xs text-muted-foreground">
            <span>{{ word.review_data.repetitions }} reviews</span>
            <span>Next: {{ formatNextReview(word.review_data.next_review_date) }}</span>
          </div>
        </div>

        <!-- Action buttons (hidden by default, shown on hover) -->
        <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <DropdownMenu>
            <DropdownMenuTrigger as-child @click.stop>
              <Button variant="ghost" size="sm" class="h-6 w-6 p-0 bg-background/80 backdrop-blur-sm">
                <MoreVertical class="h-3 w-3" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem @click.stop="startReview">
                <BookOpen class="h-3 w-3 mr-2" />
                Review
              </DropdownMenuItem>
              <DropdownMenuItem @click.stop="$emit('edit', word)">
                <Edit2 class="h-3 w-3 mr-2" />
                Edit Notes
              </DropdownMenuItem>
              <DropdownMenuItem @click.stop="markAsVisited">
                <Eye class="h-3 w-3 mr-2" />
                Mark Visited
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem @click.stop="removeFromList" class="text-destructive">
                <Trash2 class="h-3 w-3 mr-2" />
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </ThemedCard>
    </HoverCardTrigger>
    
    <HoverCardContent class="w-80 themed-hovercard" side="top">
      <div class="space-y-4">
        <!-- Header -->
        <div class="flex items-center justify-between">
          <div>
            <h4 class="font-semibold text-lg">{{ word.text }}</h4>
            <p class="text-sm text-muted-foreground">
              {{ getMasteryLabel(word.mastery_level) }} • {{ word.temperature === 'hot' ? 'Recently studied' : 'Not recently studied' }}
            </p>
          </div>
          <div class="text-2xl">
            {{ getMasteryEmoji(word.mastery_level) }}
          </div>
        </div>

        <!-- Learning Statistics -->
        <div class="grid grid-cols-2 gap-3">
          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">Reviews</div>
            <div class="font-semibold">{{ word.review_data.repetitions }}</div>
          </div>
          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">Ease Factor</div>
            <div class="font-semibold">{{ word.review_data.ease_factor.toFixed(1) }}</div>
          </div>
          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">Interval</div>
            <div class="font-semibold">{{ word.review_data.interval }}d</div>
          </div>
          <div class="space-y-1">
            <div class="text-xs text-muted-foreground">Lapses</div>
            <div class="font-semibold">{{ word.review_data.lapse_count }}</div>
          </div>
        </div>

        <!-- Timeline -->
        <div class="space-y-2">
          <div class="text-xs font-medium text-muted-foreground">Timeline</div>
          <div class="space-y-1 text-xs">
            <div class="flex justify-between">
              <span>Added:</span>
              <span>{{ formatDate(word.added_date) }}</span>
            </div>
            <div v-if="word.last_visited" class="flex justify-between">
              <span>Last visited:</span>
              <span>{{ formatDate(word.last_visited) }}</span>
            </div>
            <div class="flex justify-between">
              <span>Next review:</span>
              <span :class="isDueForReview ? 'text-primary font-medium' : ''">
                {{ formatDate(word.review_data.next_review_date) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Tags -->
        <div v-if="word.tags.length > 0" class="space-y-2">
          <div class="text-xs font-medium text-muted-foreground">Tags</div>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="tag in word.tags"
              :key="tag"
              class="inline-block px-2 py-1 text-xs bg-muted rounded-full"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <!-- Notes -->
        <div v-if="word.notes" class="space-y-2">
          <div class="text-xs font-medium text-muted-foreground">Notes</div>
          <div class="text-sm bg-muted/50 rounded-md p-2">
            {{ word.notes }}
          </div>
        </div>

        <!-- Quick actions -->
        <div class="flex gap-2 pt-2 border-t">
          <Button size="sm" @click="startReview" class="flex-1">
            <BookOpen class="h-3 w-3 mr-1" />
            Review
          </Button>
          <Button size="sm" variant="outline" @click="$emit('edit', word)">
            <Edit2 class="h-3 w-3 mr-1" />
            Edit
          </Button>
        </div>
      </div>
    </HoverCardContent>
  </HoverCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { 
  BookOpen, 
  Edit2, 
  Eye, 
  MoreVertical, 
  Trash2 
} from 'lucide-vue-next';
import { ThemedCard } from '@/components/custom/card';
import { Button } from '@/components/ui/button';
import { 
  HoverCard, 
  HoverCardContent, 
  HoverCardTrigger 
} from '@/components/ui/hover-card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { WordListItem, MasteryLevel } from '@/types';

interface Props {
  word: WordListItem;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  click: [word: WordListItem];
  review: [word: WordListItem, quality: number];
  edit: [word: WordListItem];
}>();

// Computed properties
const isDueForReview = computed(() => {
  const now = new Date();
  const reviewDate = new Date(props.word.review_data.next_review_date);
  return reviewDate <= now;
});

const progressPercentage = computed(() => {
  // Calculate progress based on mastery level and review history
  const baseProgress = {
    bronze: 25,
    silver: 60,
    gold: 100
  }[props.word.mastery_level];
  
  // Add bonus for successful reviews
  const reviewBonus = Math.min(props.word.review_data.repetitions * 2, 20);
  
  return Math.min(baseProgress + reviewBonus, 100);
});

// Methods
const getMasteryLabel = (level: MasteryLevel): string => {
  return {
    bronze: 'Learning',
    silver: 'Familiar', 
    gold: 'Mastered'
  }[level];
};

const getMasteryEmoji = (level: MasteryLevel): string => {
  return {
    bronze: '🥉',
    silver: '🥈',
    gold: '🥇'
  }[level];
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  
  return date.toLocaleDateString();
};

const formatNextReview = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays <= 0) return 'Now';
  if (diffDays === 1) return 'Tomorrow';
  if (diffDays < 7) return `${diffDays}d`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w`;
  
  return `${Math.floor(diffDays / 30)}m`;
};

const startReview = () => {
  // For now, simulate a good review (quality 4)
  // In a real implementation, this would open a review modal
  emit('review', props.word, 4);
};

const markAsVisited = () => {
  // Mark word as visited without formal review
  console.log('Marking as visited:', props.word.text);
};

const removeFromList = () => {
  // Remove word from wordlist
  console.log('Removing from list:', props.word.text);
};
</script>

<style scoped>
/* Custom styling for the themed card in this context */
.themed-title {
  background: linear-gradient(135deg, currentColor 0%, currentColor 100%);
  background-clip: text;
  -webkit-background-clip: text;
}

.themed-hovercard {
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

:root.dark .themed-hovercard {
  background: rgba(0, 0, 0, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Apple-style spring easing */
.ease-apple-spring {
  transition-timing-function: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
</style>