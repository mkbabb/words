# PWA Technical Implementation Guide

## Frontend Implementation

### 1. Web App Manifest
```json
{
  "name": "Floridify - AI-Enhanced Dictionary",
  "short_name": "Floridify",
  "description": "Discover words with AI-powered definitions and meanings",
  "start_url": "/?source=pwa",
  "display": "standalone",
  "orientation": "portrait",
  "theme_color": "#faf8f6",
  "background_color": "#faf8f6",
  "categories": ["education", "reference", "books"],
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ],
  "screenshots": [
    {
      "src": "/screenshots/home.png",
      "sizes": "1170x2532",
      "type": "image/png"
    }
  ],
  "shortcuts": [
    {
      "name": "Word of the Day",
      "url": "/word-of-the-day",
      "icons": [{ "src": "/icons/wotd.png", "sizes": "96x96" }]
    }
  ]
}
```

### 2. Service Worker Implementation
```typescript
// service-worker.ts
import { precacheAndRoute } from 'workbox-precaching';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate, CacheFirst } from 'workbox-strategies';
import { CacheableResponsePlugin } from 'workbox-cacheable-response';
import { ExpirationPlugin } from 'workbox-expiration';

// Precache static assets
precacheAndRoute(self.__WB_MANIFEST);

// API caching strategy
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/v1/search'),
  new StaleWhileRevalidate({
    cacheName: 'search-cache',
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 7 * 24 * 60 * 60, // 7 days
      }),
    ],
  })
);

// Handle push notifications
self.addEventListener('push', (event) => {
  const options = {
    body: event.data?.text() || 'New word available!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      { action: 'explore', title: 'Explore' },
      { action: 'close', title: 'Close' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Floridify', options)
  );
});
```

### 3. iOS-Specific Composable
```typescript
// composables/useIOSPWA.ts
import { ref, computed, onMounted } from 'vue';
import { useEventListener } from '@vueuse/core';

export function useIOSPWA() {
  const isIOS = ref(false);
  const isInstalled = ref(false);
  const safeAreaInsets = ref({ top: 0, bottom: 0, left: 0, right: 0 });
  const supportsPWA = ref(false);
  
  const isIPhone = computed(() => /iPhone/.test(navigator.userAgent));
  const isIPad = computed(() => /iPad/.test(navigator.userAgent));
  
  onMounted(() => {
    // Detect iOS
    isIOS.value = /iPhone|iPad|iPod/.test(navigator.userAgent);
    
    // Check if installed
    isInstalled.value = window.matchMedia('(display-mode: standalone)').matches
      || (window.navigator as any).standalone === true;
    
    // Get safe area insets
    const computedStyle = getComputedStyle(document.documentElement);
    safeAreaInsets.value = {
      top: parseInt(computedStyle.getPropertyValue('--sat') || '0'),
      bottom: parseInt(computedStyle.getPropertyValue('--sab') || '0'),
      left: parseInt(computedStyle.getPropertyValue('--sal') || '0'),
      right: parseInt(computedStyle.getPropertyValue('--sar') || '0')
    };
    
    // Check PWA support
    supportsPWA.value = 'serviceWorker' in navigator;
  });
  
  // Handle iOS viewport changes
  const fixViewportHeight = () => {
    if (isIOS.value) {
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
    }
  };
  
  useEventListener('resize', fixViewportHeight);
  useEventListener('orientationchange', fixViewportHeight);
  
  return {
    isIOS,
    isIPhone,
    isIPad,
    isInstalled,
    safeAreaInsets,
    supportsPWA,
    fixViewportHeight
  };
}
```

### 4. PWA Install Prompt Component
```vue
<!-- components/PWAInstallPrompt.vue -->
<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-500 ease-apple-spring"
      leave-active-class="transition-all duration-350 ease-apple-smooth"
      enter-from-class="opacity-0 scale-95 translate-y-8"
      leave-to-class="opacity-0 scale-95 translate-y-8"
    >
      <div
        v-if="showPrompt"
        class="fixed bottom-6 left-6 right-6 z-50 max-w-md mx-auto"
      >
        <div
          class="cartoon-shadow-md rounded-2xl bg-background/95 backdrop-blur-xl 
                 border-2 border-border p-6 space-y-4 texture-paper-clean"
        >
          <!-- iOS-specific instructions -->
          <div v-if="isIOS && !isInstalled" class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="rounded-xl bg-primary/10 p-3">
                <Share class="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-foreground">
                  Install Floridify
                </h3>
                <p class="text-sm text-muted-foreground">
                  Add to your home screen for the best experience
                </p>
              </div>
            </div>
            
            <div class="space-y-3 text-sm">
              <div class="flex items-center gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 
                           flex items-center justify-center text-xs font-semibold">
                  1
                </div>
                <p>Tap the <Share class="inline h-4 w-4" /> share button below</p>
              </div>
              
              <div class="flex items-center gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 
                           flex items-center justify-center text-xs font-semibold">
                  2
                </div>
                <p>Scroll down and tap "Add to Home Screen"</p>
              </div>
              
              <div class="flex items-center gap-3">
                <div class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 
                           flex items-center justify-center text-xs font-semibold">
                  3
                </div>
                <p>Tap "Add" to install</p>
              </div>
            </div>
            
            <div class="flex gap-3">
              <button
                @click="dismissPrompt"
                class="flex-1 px-4 py-2 rounded-xl border-2 border-border
                       text-foreground hover-lift transition-smooth"
              >
                Maybe later
              </button>
              <button
                @click="dismissPromptPermanently"
                class="px-4 py-2 rounded-xl text-muted-foreground
                       hover:text-foreground transition-smooth"
              >
                Don't show again
              </button>
            </div>
          </div>
          
          <!-- Android/Desktop prompt -->
          <div v-else-if="deferredPrompt" class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="rounded-xl bg-primary/10 p-3">
                <Download class="h-6 w-6 text-primary" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-foreground">
                  Install Floridify
                </h3>
                <p class="text-sm text-muted-foreground">
                  Install our app for offline access and notifications
                </p>
              </div>
            </div>
            
            <div class="flex gap-3">
              <button
                @click="installPWA"
                class="flex-1 px-4 py-3 rounded-xl bg-primary text-primary-foreground
                       font-medium hover-lift cartoon-shadow-sm transition-smooth"
              >
                Install App
              </button>
              <button
                @click="dismissPrompt"
                class="px-4 py-3 rounded-xl border-2 border-border
                       text-foreground hover-lift transition-smooth"
              >
                Not now
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Share, Download } from 'lucide-vue-next';
import { useIOSPWA } from '@/composables/useIOSPWA';

const { isIOS, isInstalled } = useIOSPWA();
const showPrompt = ref(false);
const deferredPrompt = ref<any>(null);

const dismissPrompt = () => {
  showPrompt.value = false;
  // Show again after 7 days
  localStorage.setItem('pwa-prompt-dismissed', Date.now().toString());
};

const dismissPromptPermanently = () => {
  showPrompt.value = false;
  localStorage.setItem('pwa-prompt-dismissed', 'permanent');
};

const installPWA = async () => {
  if (deferredPrompt.value) {
    deferredPrompt.value.prompt();
    const { outcome } = await deferredPrompt.value.userChoice;
    if (outcome === 'accepted') {
      showPrompt.value = false;
    }
    deferredPrompt.value = null;
  }
};

onMounted(() => {
  // Check if should show prompt
  const dismissed = localStorage.getItem('pwa-prompt-dismissed');
  if (dismissed === 'permanent') return;
  
  if (dismissed) {
    const dismissedTime = parseInt(dismissed);
    const daysSince = (Date.now() - dismissedTime) / (1000 * 60 * 60 * 24);
    if (daysSince < 7) return;
  }
  
  // Listen for install prompt
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt.value = e;
    // Show after user has engaged with the app
    setTimeout(() => {
      showPrompt.value = true;
    }, 30000); // 30 seconds
  });
  
  // iOS prompt logic
  if (isIOS.value && !isInstalled.value) {
    // Show after user has searched for a word
    const checkEngagement = () => {
      const hasSearched = sessionStorage.getItem('has-searched');
      if (hasSearched) {
        showPrompt.value = true;
        window.removeEventListener('word-searched', checkEngagement);
      }
    };
    window.addEventListener('word-searched', checkEngagement);
  }
});
</script>
```

## Notification Server Implementation

### 1. Server Structure
```typescript
// notification-server/src/server.ts
import express from 'express';
import webpush from 'web-push';
import { MongoClient } from 'mongodb';
import cron from 'node-cron';
import { z } from 'zod';

// Environment configuration
const config = {
  port: process.env.PORT || 3001,
  mongoUri: process.env.MONGO_URI || 'mongodb://localhost:27017',
  vapidPublicKey: process.env.VAPID_PUBLIC_KEY!,
  vapidPrivateKey: process.env.VAPID_PRIVATE_KEY!,
  vapidSubject: process.env.VAPID_SUBJECT || 'mailto:admin@floridify.com'
};

// VAPID setup
webpush.setVapidDetails(
  config.vapidSubject,
  config.vapidPublicKey,
  config.vapidPrivateKey
);

// Subscription schema
const SubscriptionSchema = z.object({
  endpoint: z.string().url(),
  keys: z.object({
    p256dh: z.string(),
    auth: z.string()
  }),
  userId: z.string().optional(),
  timezone: z.string().default('UTC'),
  preferences: z.object({
    wordOfDay: z.boolean().default(true),
    achievements: z.boolean().default(true)
  }).default({})
});

// Express app
const app = express();
app.use(express.json());

// Subscribe endpoint
app.post('/api/subscribe', async (req, res) => {
  try {
    const subscription = SubscriptionSchema.parse(req.body);
    
    // Store in MongoDB
    await db.collection('push_subscriptions').updateOne(
      { endpoint: subscription.endpoint },
      { $set: { ...subscription, updatedAt: new Date() } },
      { upsert: true }
    );
    
    res.status(201).json({ message: 'Subscription stored' });
  } catch (error) {
    res.status(400).json({ error: 'Invalid subscription' });
  }
});

// Word of the Day scheduler
cron.schedule('0 9 * * *', async () => {
  const word = await getWordOfDay();
  const subscriptions = await db.collection('push_subscriptions')
    .find({ 'preferences.wordOfDay': true })
    .toArray();
  
  const notification = {
    title: '📖 Word of the Day',
    body: `${word.word}: ${word.shortDefinition}`,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    data: {
      url: `/definition/${word.word}`,
      word: word.word
    }
  };
  
  // Send notifications in batches
  const batchSize = 100;
  for (let i = 0; i < subscriptions.length; i += batchSize) {
    const batch = subscriptions.slice(i, i + batchSize);
    await Promise.allSettled(
      batch.map(sub => 
        webpush.sendNotification(sub, JSON.stringify(notification))
          .catch(async (error) => {
            if (error.statusCode === 410) {
              // Remove expired subscription
              await db.collection('push_subscriptions')
                .deleteOne({ endpoint: sub.endpoint });
            }
          })
      )
    );
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date() });
});

app.listen(config.port, () => {
  console.log(`Notification server running on port ${config.port}`);
});
```

### 2. Docker Configuration
```dockerfile
# notification-server/Dockerfile
FROM node:20-alpine AS base
RUN apk add --no-cache curl tini

FROM base AS dependencies
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM base AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM base AS production
WORKDIR /app

# Security: non-root user
RUN addgroup -g 1001 notifier && \
    adduser -D -u 1001 -G notifier notifier

COPY --from=dependencies /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY package*.json ./

USER notifier
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3001/health || exit 1

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["node", "dist/server.js"]
```

### 3. Docker Compose Integration
```yaml
# docker-compose.notification.yml
services:
  notification-server:
    build:
      context: ./notification-server
      target: production
    container_name: floridify-notifications
    restart: unless-stopped
    ports:
      - "3001:3001"
    environment:
      NODE_ENV: production
      MONGO_URI: mongodb://mongodb:27017/floridify
      VAPID_PUBLIC_KEY: ${VAPID_PUBLIC_KEY}
      VAPID_PRIVATE_KEY: ${VAPID_PRIVATE_KEY}
      VAPID_SUBJECT: mailto:notifications@floridify.com
    networks:
      - floridify-network
    depends_on:
      - mongodb
    volumes:
      - notification-logs:/app/logs

volumes:
  notification-logs:
    driver: local
```

## Production Deployment Script

```bash
#!/bin/bash
# deploy-pwa.sh

set -e

echo "🚀 Deploying PWA features to production..."

# Build notification server
echo "📦 Building notification server..."
cd notification-server
docker build -t floridify-notification-server:latest .

# Update frontend with PWA assets
echo "🎨 Building frontend with PWA support..."
cd ../frontend
npm run build

# Deploy to EC2
echo "📤 Deploying to EC2..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.env' \
  ./dist/ ec2-user@your-ec2-ip:/var/www/floridify/

# Update Docker services
echo "🐳 Updating Docker services..."
ssh ec2-user@your-ec2-ip << 'EOF'
  cd /opt/floridify
  docker-compose -f docker-compose.yml -f docker-compose.notification.yml up -d
  docker-compose logs -f notification-server
EOF

echo "✅ PWA deployment complete!"
```

This technical guide provides the complete implementation details for adding PWA support to Floridify with a focus on iOS compatibility and modern development practices.