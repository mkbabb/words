import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createPersistedState } from 'pinia-plugin-persistedstate';
import { clerkPlugin } from '@clerk/vue';
import App from './App.vue';
import router from './router';
import { logger } from '@/utils/logger';
import { validatePersistedState } from '@/utils/validatePersistedState';

// Import Tailwind CSS and custom styles
import './assets/index.css';
// iOS PWA styles loaded conditionally in useIOSPWA composable

// Create app
const app = createApp(App);

// Create Pinia with persistence plugin + hydration validation
const pinia = createPinia();
pinia.use(createPersistedState({
  afterHydrate: (ctx) => {
    validatePersistedState({ store: ctx.store });
  },
}));

// Use plugins
app.use(pinia);
app.use(router);

// Initialize Clerk authentication
const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
if (clerkPubKey) {
  app.use(clerkPlugin, {
    publishableKey: clerkPubKey,
    routerPush: (to: string) => router.push(to),
    routerReplace: (to: string) => router.replace(to),
  });
} else {
  logger.warn('VITE_CLERK_PUBLISHABLE_KEY not set — auth disabled');
}

// Add global error handler for Reka UI getBoundingClientRect errors
app.config.errorHandler = (err, _vm, info) => {
  // Check if this is the specific Reka UI getBoundingClientRect error
  if (err instanceof TypeError && 
      err.message.includes("Cannot read properties of null (reading 'getBoundingClientRect')")) {
    logger.warn('Reka UI getBoundingClientRect error caught and handled during component transition:', err.message)
    // Don't rethrow the error - just log it and continue
    return
  }

  // For other errors, log and potentially rethrow
  logger.error('Unhandled Vue error:', err, info)
  // You could add error reporting here if needed
}

// Also add window error handler for any errors that escape Vue's error handling
window.addEventListener('error', (event) => {
  if (event.error instanceof TypeError && 
      event.error.message.includes("Cannot read properties of null (reading 'getBoundingClientRect')")) {
    logger.warn('Global getBoundingClientRect error caught and handled:', event.error.message)
    event.preventDefault()
    return
  }
})

// Mount app
app.mount('#app');
