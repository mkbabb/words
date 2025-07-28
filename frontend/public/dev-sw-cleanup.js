// Development Service Worker Cleanup
// This script unregisters service workers and clears caches in development

(async function() {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('🧹 Development mode: Cleaning up service workers and caches...');
    
    // Unregister all service workers
    if ('serviceWorker' in navigator) {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const registration of registrations) {
        const success = await registration.unregister();
        console.log(`Service worker unregistered: ${success ? '✅' : '❌'}`);
      }
    }
    
    // Clear all caches
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      for (const cacheName of cacheNames) {
        await caches.delete(cacheName);
        console.log(`Cache deleted: ${cacheName}`);
      }
    }
    
    // Clear localStorage PWA data
    const pwaCacheKey = 'floridify-pwa-cache-cleared';
    const lastCleared = localStorage.getItem(pwaCacheKey);
    const now = Date.now();
    
    // Clear once per hour to avoid constant clearing
    if (!lastCleared || now - parseInt(lastCleared) > 3600000) {
      localStorage.setItem(pwaCacheKey, now.toString());
      console.log('✅ Service workers and caches cleared for development');
    }
  }
})();