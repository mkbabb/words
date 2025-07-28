// Floridify Service Worker
const CACHE_NAME = 'floridify-v2'; // Increment to force update
const STATIC_CACHE = 'floridify-static-v2';
const API_CACHE = 'floridify-api-v2';

// Critical resources to cache immediately
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/assets/index.css',
  '/assets/themed-cards.css'
];

// Install event - cache critical resources
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  // Skip waiting to activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('floridify-') && name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // DEVELOPMENT MODE: Skip caching for Vite HMR and development assets
  const isDevelopment = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
  if (isDevelopment) {
    // Skip caching for Vite HMR WebSocket
    if (url.pathname.includes('/@vite') || 
        url.pathname.includes('/__vite') ||
        url.pathname.includes('/.vite') ||
        url.pathname.includes('/node_modules') ||
        url.pathname.includes('.hot-update') ||
        url.pathname.includes('@fs') ||
        url.pathname.includes('@id') ||
        request.url.includes('?t=') || // Vite timestamp queries
        request.url.includes('&t=') ||
        url.protocol === 'ws:' || 
        url.protocol === 'wss:') {
      return; // Let the request pass through without service worker intervention
    }

    // For development, use network-only for all resources to ensure fresh content
    if (url.pathname.includes('/src/') || 
        url.pathname.includes('.vue') ||
        url.pathname.includes('.ts') ||
        url.pathname.includes('.tsx') ||
        url.pathname.includes('.jsx')) {
      return; // Skip service worker entirely for source files
    }
  }

  // API calls - Stale While Revalidate
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(staleWhileRevalidate(request, API_CACHE));
    return;
  }

  // Static assets - Cache First (only in production)
  if (!isDevelopment && (
      request.destination === 'style' || 
      request.destination === 'script' || 
      request.destination === 'image' ||
      url.pathname.includes('/assets/'))) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // HTML pages - Network First with fallback
  if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirst(request, STATIC_CACHE));
    return;
  }

  // Default - Network First
  event.respondWith(networkFirst(request, CACHE_NAME));
});

// Push notification handling
self.addEventListener('push', (event) => {
  const options = event.data ? event.data.json() : {
    title: 'Floridify',
    body: 'Check out the word of the day!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      { action: 'explore', title: 'Explore', icon: '/icons/action-explore.png' },
      { action: 'close', title: 'Dismiss', icon: '/icons/action-close.png' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(options.title, options)
  );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'close') return;

  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Try to focus an existing window
      for (const client of clientList) {
        if (client.url.includes('floridify') && 'focus' in client) {
          return client.focus().then(() => {
            if ('navigate' in client) {
              return client.navigate(urlToOpen);
            }
          });
        }
      }
      // Open new window if needed
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-searches') {
    event.waitUntil(syncOfflineSearches());
  }
});

// Caching strategies
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  
  if (cached) {
    return cached;
  }
  
  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Return offline page if available
    const offlinePage = await cache.match('/offline.html');
    return offlinePage || new Response('Offline', { status: 503 });
  }
}

async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  
  const fetchPromise = fetch(request).then((response) => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  });
  
  return cached || fetchPromise;
}

// Sync offline searches when back online
async function syncOfflineSearches() {
  const searches = await getOfflineSearches();
  
  for (const search of searches) {
    try {
      await fetch('/api/v1/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(search)
      });
      await removeOfflineSearch(search.id);
    } catch (error) {
      console.error('Failed to sync search:', error);
    }
  }
}

// IndexedDB helpers for offline data
async function getOfflineSearches() {
  // Implementation would use IndexedDB
  return [];
}

async function removeOfflineSearch(id) {
  // Implementation would use IndexedDB
}

// Listen for skip waiting message
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});