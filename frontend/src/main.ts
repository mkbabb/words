import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createPersistedState } from 'pinia-plugin-persistedstate';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import Home from './views/Home.vue';

// Import Tailwind CSS and custom styles
import './assets/index.css';
import './styles/ios-pwa.css';

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: Home,
    },
    {
      path: '/search/:query?',
      name: 'Search',
      component: Home,
      props: true,
    },
    {
      path: '/definition/:word',
      name: 'Definition',
      component: Home,
      props: true,
    },
    {
      path: '/thesaurus/:word',
      name: 'Thesaurus',
      component: Home,
      props: true,
    },
    {
      path: '/wordlist/:wordlistId',
      name: 'Wordlist',
      component: Home,
      props: true,
    },
    {
      path: '/wordlist/:wordlistId/search/:query?',
      name: 'WordlistSearch',
      component: Home,
      props: true,
    },
  ],
});

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
        .then(registration => {
          console.log('Service Worker registered:', registration);
        })
        .catch(error => {
          console.error('Service Worker registration failed:', error);
        });
    });
  } else {
    console.log('⚠️ Service Worker registration skipped in development mode to prevent caching issues');
  }
}

// Add global error handler for Reka UI getBoundingClientRect errors
app.config.errorHandler = (err, vm, info) => {
  // Check if this is the specific Reka UI getBoundingClientRect error
  if (err instanceof TypeError && 
      err.message.includes("Cannot read properties of null (reading 'getBoundingClientRect')")) {
    console.warn('Reka UI getBoundingClientRect error caught and handled during component transition:', err.message)
    // Don't rethrow the error - just log it and continue
    return
  }
  
  // For other errors, log and potentially rethrow
  console.error('Unhandled Vue error:', err, info)
  // You could add error reporting here if needed
}

// Also add window error handler for any errors that escape Vue's error handling
window.addEventListener('error', (event) => {
  if (event.error instanceof TypeError && 
      event.error.message.includes("Cannot read properties of null (reading 'getBoundingClientRect')")) {
    console.warn('Global getBoundingClientRect error caught and handled:', event.error.message)
    event.preventDefault()
    return
  }
})

// Mount app
app.mount('#app');
