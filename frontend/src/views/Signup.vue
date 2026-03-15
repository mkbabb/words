<template>
  <div
    class="flex min-h-screen flex-col items-center justify-center px-4"
    :style="{
      backgroundImage: 'var(--paper-clean-texture)',
      backgroundAttachment: 'fixed',
      backgroundSize: '60px 60px',
    }"
  >
    <!-- Card container -->
    <div
      class="flex w-full max-w-md flex-col items-center rounded-2xl glass-light p-8 cartoon-shadow-sm"
    >
      <!-- Branding -->
      <div class="mb-6 flex flex-col items-center gap-2">
        <FloridifyIcon expanded :show-subscript="false" class="text-2xl" />
        <p class="text-muted-foreground text-sm">AI-enhanced dictionary</p>
      </div>

      <!-- Clerk Sign Up (renders when Clerk loads on the correct domain) -->
      <div v-if="hasClerk" class="w-full">
        <ClerkLoaded>
          <SignUp
            :appearance="clerkAppearance"
            :routing="'path'"
            :path="'/signup'"
            :sign-in-url="'/login'"
            :after-sign-up-url="'/'"
          />
        </ClerkLoaded>
      </div>
    </div>

    <!-- Back link -->
    <router-link
      to="/"
      class="text-muted-foreground hover:text-foreground mt-6 text-sm transition-colors"
    >
      Continue without signing up
    </router-link>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { SignUp, ClerkLoaded } from '@clerk/vue';
import FloridifyIcon from '@/components/custom/icons/FloridifyIcon.vue';

const hasClerk = !!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

const clerkAppearance = computed(() => ({
  variables: {
    fontFamily: 'Fraunces, Georgia, serif',
    colorPrimary: 'hsl(var(--primary))',
    colorBackground: 'transparent',
    colorText: 'hsl(var(--card-foreground))',
    colorInputBackground: 'hsl(var(--input))',
    colorInputText: 'hsl(var(--foreground))',
    borderRadius: '0.75rem',
  },
  layout: {
    socialButtonsPlacement: 'top' as const,
  },
  elements: {
    rootBox: 'w-full shadow-none',
    card: 'bg-transparent shadow-none border-0 p-0 w-full',
    socialButtonsBlockButton:
      'rounded-xl border border-border bg-background hover:bg-accent transition-colors font-serif',
    formFieldInput: 'rounded-xl border-border bg-background font-serif',
    formButtonPrimary:
      'bg-primary text-primary-foreground hover:bg-primary/90 rounded-xl transition-colors font-serif',
    headerTitle: 'font-serif',
    headerSubtitle: 'font-serif text-muted-foreground',
    footerAction: 'font-serif',
  },
}));
</script>
