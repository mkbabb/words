import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import Home from './views/Home.vue';

// Import Tailwind CSS and custom styles
import './assets/index.css';

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

// Mount app
app.mount('#app');
