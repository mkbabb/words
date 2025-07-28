# Floridify PWA Testing & Deployment Guide

## Overview

This guide covers testing and deploying the PWA features for Floridify, with special attention to iOS compatibility and push notifications.

## Local Testing Setup

### 1. Generate VAPID Keys
```bash
cd notification-server
npm install
npm run generate-vapid-keys
```

This creates a `.env` file with your VAPID keys. Copy the public key to `frontend/.env`:
```
VITE_VAPID_PUBLIC_KEY=your_public_key_here
```

### 2. Start All Services
```bash
# Using Docker Compose (recommended)
docker-compose -f docker-compose.yml -f docker-compose.notification.yml up

# Or start individually
cd backend && uvicorn src.floridify.api.main:app --reload
cd frontend && npm run dev
cd notification-server && npm run dev
```

### 3. Test PWA Installation

#### iOS Testing
1. **Open in Safari** (Chrome/Firefox won't work for PWA on iOS)
2. Navigate to `https://localhost:3000` (use ngrok for HTTPS)
3. Search for 3+ words to trigger install prompt
4. Tap Share → Add to Home Screen

#### Android Testing
1. Open in Chrome
2. Look for install prompt after 30 seconds
3. Or use Chrome menu → Install app

#### Desktop Testing
1. Chrome/Edge: Look for install icon in address bar
2. Or use browser menu → Install Floridify

### 4. Test Push Notifications

#### Enable Notifications
1. Install the PWA first (required on iOS)
2. Search for 5+ words and view 3+ definitions
3. Notification prompt should appear
4. Click "Enable Notifications"

#### Test Notification Delivery
```bash
# Send test notification
curl -X POST http://localhost:3001/api/send-notification \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "test-user",
    "notification": {
      "title": "Test Notification",
      "body": "This is a test notification",
      "icon": "/icons/icon-192x192.png"
    }
  }'
```

## iOS-Specific Testing

### Requirements
- iOS 16.4+ for push notifications
- Safari browser (no other browsers support PWA on iOS)
- Must be installed to home screen for notifications

### Test Checklist
- [ ] Safe area insets working (notched devices)
- [ ] Status bar styling correct
- [ ] Swipe navigation gestures
- [ ] Keyboard doesn't break layout
- [ ] Offline mode works
- [ ] Icons and splash screens display
- [ ] Push notifications (after install)

### Debugging Tools
```javascript
// In Safari console
navigator.serviceWorker.getRegistrations()
  .then(regs => console.log('Service Workers:', regs));

// Check push subscription
navigator.serviceWorker.ready
  .then(reg => reg.pushManager.getSubscription())
  .then(sub => console.log('Push subscription:', sub));

// Check IndexedDB storage
navigator.storage.estimate()
  .then(estimate => console.log('Storage:', estimate));
```

## Production Deployment

### 1. Environment Setup
Create production `.env` files:

```bash
# backend/.env.production
ENVIRONMENT=production
BACKEND_CORS_ORIGINS=["https://floridify.com"]

# frontend/.env.production
VITE_API_URL=https://api.floridify.com
VITE_VAPID_PUBLIC_KEY=your_production_public_key

# notification-server/.env.production
NODE_ENV=production
VAPID_PUBLIC_KEY=your_production_public_key
VAPID_PRIVATE_KEY=your_production_private_key
MONGO_URI=mongodb://production-mongo:27017
API_URL=http://backend:8000
CORS_ORIGINS=https://floridify.com
```

### 2. Build and Deploy
```bash
# Run deployment script
./scripts/deploy-pwa.sh

# Or manual deployment
docker-compose \
  -f docker-compose.yml \
  -f docker-compose.notification.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.notification.yml \
  up -d
```

### 3. Nginx Configuration
Add to your nginx site config:
```nginx
server {
    server_name floridify.com;
    
    # PWA essentials
    location /manifest.json {
        add_header Content-Type application/manifest+json;
    }
    
    location /service-worker.js {
        add_header Service-Worker-Allowed /;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }
    
    # Icons and assets
    location ~ ^/(icons|screenshots)/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Notification server proxy
    location /api/v1/push/ {
        proxy_pass http://localhost:3001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. SSL Certificate
PWAs require HTTPS:
```bash
# Using Let's Encrypt
sudo certbot --nginx -d floridify.com -d www.floridify.com
```

## Monitoring & Maintenance

### Health Checks
```bash
# Check all services
curl https://floridify.com/api/v1/health
curl https://floridify.com/api/v1/push/health

# Check Docker containers
docker ps
docker logs floridify-notifications
```

### Database Maintenance
```javascript
// Check push subscription stats
db.push_subscriptions.countDocuments({ isActive: true })

// Check notification logs
db.notification_logs.find().sort({ timestamp: -1 }).limit(10)

// Clean expired subscriptions (runs automatically)
db.push_subscriptions.deleteMany({
  isActive: false,
  expiredAt: { $lt: new Date(Date.now() - 30*24*60*60*1000) }
})
```

### Common Issues

#### iOS Not Showing Install Prompt
- Ensure using Safari (not Chrome/Firefox)
- Check meta tags in index.html
- Verify manifest.json is served correctly
- Clear Safari cache and try again

#### Push Notifications Not Working
- Check VAPID keys match between frontend and backend
- Ensure service worker is registered
- Verify notification permissions granted
- Check browser console for errors

#### Service Worker Not Updating
```javascript
// Force update in console
navigator.serviceWorker.getRegistration()
  .then(reg => reg.update());

// Or clear everything
navigator.serviceWorker.getRegistrations()
  .then(regs => regs.forEach(reg => reg.unregister()));
```

## Performance Optimization

### Lighthouse PWA Audit
1. Open Chrome DevTools
2. Go to Lighthouse tab
3. Select "Progressive Web App" category
4. Run audit

Target scores:
- Performance: 90+
- PWA: 100
- Best Practices: 95+

### Cache Strategy
- Static assets: Cache First (1 year)
- API calls: Stale While Revalidate
- HTML: Network First with fallback

### Bundle Size
Keep service worker under 50KB:
```bash
# Check service worker size
ls -lh public/service-worker.js

# Analyze frontend bundle
cd frontend && npm run build -- --analyze
```

## Rollback Procedure

If issues arise after deployment:

```bash
# 1. Revert to previous version
docker-compose down
git checkout previous-tag

# 2. Rebuild and deploy
./scripts/deploy-pwa.sh

# 3. Clear CDN cache if applicable
# 4. Notify users to refresh
```

## Success Metrics

Monitor these KPIs after launch:
- PWA installation rate
- Push notification opt-in rate
- Notification click-through rate
- Offline usage statistics
- Performance metrics (Core Web Vitals)

## Support Resources

- [PWA Builder](https://www.pwabuilder.com/) - Test your PWA
- [What PWA Can Do Today](https://whatpwacando.today/) - Feature support
- [iOS PWA Limitations](https://firt.dev/ios-pwa/) - Current iOS restrictions
- [Web Push Tester](https://web-push-codelab.glitch.me/) - Test push notifications