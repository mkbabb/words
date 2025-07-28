# Floridify PWA Implementation Plan

## Executive Summary

This plan outlines the implementation of Progressive Web App (PWA) functionality for Floridify, with a focus on iOS compatibility and push notifications for "Word of the Day" features. The implementation follows the existing codebase's modern Tailwind CSS patterns and Vue 3 architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                          │
├─────────────────────────────────────────────────────────────────┤
│  - PWA Manifest & Service Worker                                │
│  - iOS-specific composables (useIOSPWA)                         │  
│  - Install prompts with Tailwind styling                        │
│  - Push notification subscription UI                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Notification Server (Node.js)                  │
├─────────────────────────────────────────────────────────────────┤
│  - VAPID key management                                         │
│  - Push subscription storage (MongoDB)                          │
│  - Word of the Day scheduler                                   │
│  - Multi-platform push delivery                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure (Docker)                       │
├─────────────────────────────────────────────────────────────────┤
│  - Containerized notification server                            │
│  - Integration with existing Docker Compose                    │
│  - EC2 production deployment                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: PWA Foundation
1. **Web App Manifest** - Configure app metadata, icons, theme colors
2. **Service Worker** - Implement caching, offline support, background sync
3. **iOS Meta Tags** - Add Apple-specific PWA configuration

### Phase 2: iOS-Specific Features  
1. **Safe Area Handling** - Support for notched devices and Dynamic Island
2. **Gesture Navigation** - Swipe-to-navigate, pull-to-refresh
3. **Install Prompts** - Custom iOS installation instructions

### Phase 3: Push Notifications
1. **Permission Flow** - Contextual permission requests with pre-prompts
2. **Subscription Management** - Store and manage push subscriptions
3. **Notification Server** - Node.js server with VAPID authentication

### Phase 4: Word of the Day
1. **Scheduler Service** - Cron-based daily word selection
2. **Timezone Support** - Send notifications at optimal local times
3. **Rich Notifications** - Include word preview and definition teaser

### Phase 5: Production Deployment
1. **Docker Configuration** - Multi-stage builds with security hardening
2. **EC2 Integration** - Deploy alongside existing services
3. **Monitoring Setup** - Health checks and error tracking

## Design Principles

### Tailwind CSS Integration
- Follow existing utility patterns: `transition-smooth`, `hover-lift`, `cartoon-shadow-sm`
- Use theme colors: `bg-background`, `text-foreground`, `border-border`
- Maintain paper texture aesthetics with `texture-paper-clean`
- Apply consistent animations: `ease-apple-spring`, `duration-350`

### Component Architecture
```vue
<!-- Example PWA Install Prompt following codebase patterns -->
<template>
  <Transition
    enter-active-class="transition-all duration-350 ease-apple-spring"
    leave-active-class="transition-all duration-250 ease-apple-smooth"
    enter-from-class="opacity-0 scale-95 translate-y-4"
    leave-to-class="opacity-0 scale-95 translate-y-4"
  >
    <div v-if="showPrompt" 
         class="fixed bottom-6 left-6 right-6 z-50 max-w-md mx-auto">
      <div class="cartoon-shadow-md rounded-2xl bg-background/95 backdrop-blur-xl 
                  border-2 border-border p-6 space-y-4">
        <!-- Content -->
      </div>
    </div>
  </Transition>
</template>
```

### iOS-Specific Considerations
1. **No automatic install prompts** - Design manual installation flow
2. **Safari-only PWA support** - Test exclusively in Safari
3. **Storage limitations** - Implement data sync on app launch
4. **No background sync** - Use push notifications strategically

## Technical Specifications

### Service Worker Strategy
```javascript
// Cache-first with network fallback
const CACHE_NAME = 'floridify-v1';
const urlsToCache = [
  '/',
  '/assets/index.css',
  '/assets/themed-cards.css',
  // Critical resources
];

// Implement stale-while-revalidate for API calls
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/')) {
    event.respondWith(staleWhileRevalidate(event.request));
  } else {
    event.respondWith(cacheFirst(event.request));
  }
});
```

### Notification Server Architecture
```javascript
// Lightweight Express server with MongoDB integration
const server = {
  framework: 'Express.js',
  database: 'MongoDB (existing)',
  authentication: 'VAPID',
  scheduler: 'node-cron',
  pushLibrary: 'web-push',
  monitoring: 'Prometheus + Grafana'
};
```

### Docker Configuration
```dockerfile
# Multi-stage build for minimal image size
FROM node:20-alpine AS production
# Security hardening
RUN addgroup -g 1001 notifier && \
    adduser -D -u 1001 -G notifier notifier
# Health checks
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:3001/health || exit 1
```

## Success Metrics
- **Installation Rate**: Track PWA installations vs web visits
- **Notification Opt-in**: Measure permission grant rate
- **Engagement**: Monitor notification click-through rates
- **Performance**: Ensure <3s load time on 3G networks
- **iOS Compatibility**: 100% feature parity where possible

## Risk Mitigation
- **iOS Limitations**: Implement graceful fallbacks
- **Storage Eviction**: Regular data sync with backend
- **Notification Fatigue**: Careful frequency management
- **Browser Support**: Progressive enhancement approach

## Timeline
- Week 1: PWA foundation and iOS features
- Week 2: Notification server and permission flow
- Week 3: Word of the Day implementation
- Week 4: Testing and production deployment

This plan ensures a modern, idiomatic implementation that seamlessly integrates with Floridify's existing architecture while providing a premium PWA experience focused on iOS users.