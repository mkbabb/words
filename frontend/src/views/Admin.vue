<template>
  <div class="min-h-screen bg-background">
    <!-- Header -->
    <div class="border-b border-border bg-background/95 backdrop-blur">
      <div class="mx-auto flex max-w-4xl items-center justify-between px-6 py-4">
        <div class="flex items-center gap-3">
          <router-link to="/" class="text-muted-foreground hover:text-foreground transition-colors">
            <ArrowLeft :size="20" />
          </router-link>
          <h1 class="text-xl font-semibold">Admin Panel</h1>
          <RoleBadge role="admin" />
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="mx-auto max-w-4xl px-6 py-8 space-y-8">
      <!-- User Management -->
      <section>
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold">User Management</h2>
          <button
            @click="loadUsers"
            :disabled="loading"
            class="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm transition-colors hover:bg-accent"
          >
            <RefreshCw :class="['h-3.5 w-3.5', loading && 'animate-spin']" />
            Refresh
          </button>
        </div>

        <!-- Loading state -->
        <div v-if="loading && users.length === 0" class="space-y-3">
          <div v-for="i in 5" :key="i" class="h-16 animate-pulse rounded-lg bg-muted" />
        </div>

        <!-- Empty state -->
        <div v-else-if="users.length === 0" class="rounded-lg border border-border p-8 text-center">
          <Users :size="40" class="mx-auto mb-3 text-muted-foreground" />
          <p class="text-muted-foreground">No users found.</p>
        </div>

        <!-- User list -->
        <div v-else class="space-y-2">
          <div
            v-for="u in users"
            :key="u.clerk_id"
            class="flex items-center justify-between rounded-lg border border-border p-4 transition-colors hover:bg-accent/50"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div
                class="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border border-primary/20 bg-gradient-to-br from-primary/20 to-primary/10"
              >
                <img
                  v-if="u.avatar_url"
                  :src="u.avatar_url"
                  :alt="u.username || u.email || 'User'"
                  class="h-full w-full rounded-full object-cover"
                />
                <User v-else :size="18" class="text-primary" />
              </div>

              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="truncate font-medium">
                    {{ u.username || u.email || u.clerk_id }}
                  </span>
                  <RoleBadge :role="u.role" />
                </div>
                <div class="text-xs text-muted-foreground truncate">
                  {{ u.email || 'No email' }}
                  <span class="mx-1">&middot;</span>
                  Last login: {{ formatDate(u.last_login) }}
                </div>
              </div>
            </div>

            <!-- Role selector -->
            <div class="flex-shrink-0 ml-4">
              <select
                :value="u.role"
                @change="handleRoleChange(u.clerk_id, ($event.target as HTMLSelectElement).value as UserRole)"
                :disabled="updatingRole === u.clerk_id"
                class="rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
              >
                <option value="user">User</option>
                <option value="premium">Premium</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Stats summary -->
        <div v-if="users.length > 0" class="mt-4 flex items-center gap-6 text-sm text-muted-foreground">
          <span>{{ users.length }} total users</span>
          <span>{{ users.filter(u => u.role === 'admin').length }} admins</span>
          <span>{{ users.filter(u => u.role === 'premium').length }} premium</span>
        </div>
      </section>

      <!-- Re-synthesis Tool -->
      <section>
        <h2 class="mb-4 text-lg font-semibold">Re-synthesis Tool</h2>
        <div class="rounded-lg border border-border p-4">
          <p class="mb-3 text-sm text-muted-foreground">
            Force re-synthesis of a word's AI definition. This re-fetches provider data
            and runs the full AI synthesis pipeline from scratch.
          </p>
          <div class="flex gap-2">
            <input
              v-model="reSynthWord"
              @keydown.enter="handleReSynthesize"
              placeholder="Enter a word..."
              class="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
            <button
              @click="handleReSynthesize"
              :disabled="reSynthesizing || !reSynthWord.trim()"
              class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              <RefreshCw :class="['h-3.5 w-3.5', reSynthesizing && 'animate-spin']" />
              Re-synthesize
            </button>
          </div>
          <p v-if="reSynthResult" class="mt-2 text-sm text-green-600 dark:text-green-400">
            {{ reSynthResult }}
          </p>
          <p v-if="reSynthError" class="mt-2 text-sm text-destructive">
            {{ reSynthError }}
          </p>
        </div>
      </section>

      <!-- Wordlist Management -->
      <section>
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-lg font-semibold">Wordlist Management</h2>
          <div class="flex items-center gap-2">
            <button
              @click="loadWordlists"
              :disabled="loadingWordlists"
              class="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm transition-colors hover:bg-accent"
            >
              <RefreshCw :class="['h-3.5 w-3.5', loadingWordlists && 'animate-spin']" />
              Refresh
            </button>
          </div>
        </div>

        <!-- Loading state -->
        <div v-if="loadingWordlists && wordlists.length === 0" class="space-y-3">
          <div v-for="i in 3" :key="i" class="h-16 animate-pulse rounded-lg bg-muted" />
        </div>

        <!-- Empty state -->
        <div v-else-if="wordlists.length === 0" class="rounded-lg border border-border p-8 text-center">
          <Database :size="40" class="mx-auto mb-3 text-muted-foreground" />
          <p class="text-muted-foreground">No wordlists found.</p>
        </div>

        <!-- Wordlist table -->
        <div v-else class="space-y-2">
          <div
            v-for="wl in wordlists"
            :key="wl.id"
            class="flex items-center justify-between rounded-lg border border-border p-4 transition-colors hover:bg-accent/50"
          >
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="truncate font-medium">{{ wl.name }}</span>
                <span v-if="wl.is_public" class="rounded-full bg-green-100 dark:bg-green-900/30 px-2 py-0.5 text-micro font-medium text-green-700 dark:text-green-400">Public</span>
              </div>
              <div class="text-xs text-muted-foreground truncate">
                {{ wl.total_words }} words
                <span class="mx-1">&middot;</span>
                Owner: {{ wl.owner_id || 'unknown' }}
                <span class="mx-1">&middot;</span>
                Created: {{ formatDate(wl.created_at) }}
              </div>
            </div>
            <button
              @click="deleteWordlist(wl.id)"
              :disabled="deletingWordlist === wl.id"
              class="flex-shrink-0 ml-4 inline-flex items-center gap-1 rounded-md border border-destructive/30 px-2 py-1 text-xs text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-50"
            >
              <Trash2 :size="12" />
              Delete
            </button>
          </div>
        </div>

        <!-- Stats -->
        <div v-if="wordlists.length > 0" class="mt-4 flex items-center gap-6 text-sm text-muted-foreground">
          <span>{{ wordlists.length }} wordlists</span>
          <span>{{ wordlists.reduce((sum, wl) => sum + (wl.total_words || 0), 0) }} total words</span>
        </div>

      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ArrowLeft, RefreshCw, User, Users, Database, Trash2 } from 'lucide-vue-next';
import { useAuthStore } from '@/stores/auth';
import { usersApi } from '@/api/users';
import { lookupApi } from '@/api/lookup';
import { wordlistApi } from '@/api';
import { RoleBadge } from '@/components/custom/auth';
import type { UserProfile, UserRole } from '@/types/api/models';
import { useRouter } from 'vue-router';

const auth = useAuthStore();
const router = useRouter();

// Redirect non-admins
if (!auth.isAdmin) {
  router.replace('/');
}

// User management state
const users = ref<UserProfile[]>([]);
const loading = ref(false);
const updatingRole = ref<string | null>(null);

// Re-synthesis state
const reSynthWord = ref('');
const reSynthesizing = ref(false);
const reSynthResult = ref('');
const reSynthError = ref('');

// Wordlist management state
const wordlists = ref<any[]>([]);
const loadingWordlists = ref(false);
const deletingWordlist = ref<string | null>(null);


async function loadUsers() {
  loading.value = true;
  try {
    users.value = await usersApi.listUsers();
  } catch (e: any) {
    console.error('Failed to load users:', e);
  } finally {
    loading.value = false;
  }
}

async function handleRoleChange(clerkId: string, newRole: UserRole) {
  updatingRole.value = clerkId;
  try {
    const updated = await usersApi.updateRole(clerkId, newRole);
    // Update local state
    const idx = users.value.findIndex(u => u.clerk_id === clerkId);
    if (idx >= 0) {
      users.value[idx] = { ...users.value[idx], role: updated.role };
    }
  } catch (e: any) {
    console.error('Failed to update role:', e);
    // Revert by reloading
    await loadUsers();
  } finally {
    updatingRole.value = null;
  }
}

async function handleReSynthesize() {
  const word = reSynthWord.value.trim();
  if (!word) return;

  reSynthesizing.value = true;
  reSynthResult.value = '';
  reSynthError.value = '';

  try {
    const entry = await lookupApi.reSynthesize(word);
    const defCount = entry.definitions?.length || 0;
    reSynthResult.value = `"${word}" re-synthesized with ${defCount} definitions.`;
    reSynthWord.value = '';
  } catch (e: any) {
    reSynthError.value = e.message || 'Re-synthesis failed';
  } finally {
    reSynthesizing.value = false;
  }
}

async function loadWordlists() {
  loadingWordlists.value = true;
  try {
    const response = await wordlistApi.getWordlists({ limit: 100 });
    wordlists.value = response.items || [];
  } catch (e: any) {
    console.error('Failed to load wordlists:', e);
  } finally {
    loadingWordlists.value = false;
  }
}

async function deleteWordlist(id: string) {
  deletingWordlist.value = id;
  try {
    await wordlistApi.deleteWordlist(id);
    wordlists.value = wordlists.value.filter(wl => wl.id !== id);
  } catch (e: any) {
    console.error('Failed to delete wordlist:', e);
  } finally {
    deletingWordlist.value = null;
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Never';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

onMounted(() => {
  loadUsers();
  loadWordlists();
});
</script>
