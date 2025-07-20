<template>
  <div
    :class="{ dark: isDark }"
    class="bg-background text-foreground min-h-screen"
  >
    <!-- Dark Mode Toggle -->
    <div
      class="fixed top-0 right-0 z-50 grid items-center justify-items-center gap-2 p-2"
    >
      <DarkModeToggle style="width: 2rem; height: 2rem" />
      <div class="flex">
        <HoverCard :open-delay="0">
          <HoverCardTrigger>
            <Button variant="link" class="h-auto p-0 font-mono text-sm"
              >@mbabb</Button
            >
          </HoverCardTrigger>
          <HoverCardContent>
            <div class="flex gap-4">
              <Avatar>
                <AvatarImage
                  src="https://avatars.githubusercontent.com/u/2848617?v=4"
                />
              </Avatar>
              <div>
                <h4 class="text-sm font-semibold hover:underline">
                  <a href="https://github.com/mkbabb" class="font-mono"
                    >@mbabb</a
                  >
                </h4>
                <p class="text-muted-foreground text-sm">
                  AI-enhanced dictionary system
                </p>
              </div>
            </div>
          </HoverCardContent>
        </HoverCard>
      </div>
    </div>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { DarkModeToggle, isDark } from '@/components/custom/dark-mode-toggle';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui';
import { Avatar, AvatarImage, Button } from '@/components/ui';
</script>


