import { createApp } from 'vue';
import { createPinia } from 'pinia';
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
  ],
});

// Create app
const app = createApp(App);

// Use plugins
app.use(createPinia());
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

// Mount app
app.mount('#app');
