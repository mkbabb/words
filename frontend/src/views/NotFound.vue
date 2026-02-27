<template>
  <div class="flex min-h-screen flex-col items-center justify-center px-4 text-center">
    <h1 class="text-6xl font-bold text-foreground/80">404</h1>
    <p class="mt-4 text-lg text-muted-foreground">Page not found</p>
    <router-link
      to="/"
      class="mt-8 inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
    >
      Back to Home
    </router-link>
  </div>
</template>
