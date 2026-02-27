import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createPersistedState } from 'pinia-plugin-persistedstate';
import App from './App.vue';
import router from './router';
import { logger } from '@/utils/logger';

// Import Tailwind CSS and custom styles
import './assets/index.css';
import './styles/ios-pwa.css';

// Create app
const app = createApp(App);

// Create Pinia with persistence plugin
const pinia = createPinia();
pinia.use(createPersistedState());

// Use plugins
app.use(pinia);
app.use(router);

// Register service worker
if ('serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
        .then(() => {})
        .catch(error => {
          logger.error('Service Worker registration failed:', error);
        });
    });
  }
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
