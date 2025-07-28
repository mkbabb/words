<template>
  <div v-if="showPrompt" class="pwa-install-prompt">
    <!-- iOS Manual Install Instructions -->
    <div v-if="isIOS && !isStandalone" class="ios-install-instructions">
      <div class="install-header">
        <h3>Install Floridify</h3>
        <button @click="dismiss" class="close-btn">✕</button>
      </div>
      
      <div class="install-content">
        <p>Install this app on your iPhone for the best experience:</p>
        
        <ol class="install-steps">
          <li>
            <span class="step-icon">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 3v10m0 0l3-3m-3 3l-3-3"/>
                <path d="M3 12v5a1 1 0 001 1h12a1 1 0 001-1v-5"/>
              </svg>
            </span>
            Tap the Share button below
          </li>
          <li>
            <span class="step-icon">📱</span>
            Scroll down and tap "Add to Home Screen"
          </li>
          <li>
            <span class="step-icon">➕</span>
            Tap "Add" in the top right
          </li>
        </ol>
        
        <div class="install-benefits">
          <h4>Benefits:</h4>
          <ul>
            <li>✓ Works offline</li>
            <li>✓ Full screen experience</li>
            <li>✓ Quick access from home screen</li>
            <li>✓ Push notifications</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- Android/Desktop Install Prompt -->
    <div v-else-if="canInstall" class="standard-install-prompt">
      <div class="install-header">
        <img src="/favicon-64.png" alt="Floridify" class="app-icon">
        <div>
          <h3>Install Floridify</h3>
          <p>Add to your home screen for quick access</p>
        </div>
      </div>
      
      <div class="install-actions">
        <button @click="dismiss" class="btn-secondary">Not now</button>
        <button @click="install" class="btn-primary">Install</button>
      </div>
    </div>

    <!-- Update Available Prompt -->
    <div v-if="updateAvailable" class="update-prompt">
      <p>A new version is available!</p>
      <button @click="updateApp" class="btn-primary">Update</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useIOSPWA } from '@/composables/useIOSPWA';
import { pwaService } from '@/services/pwa.service';

const { isIOS, isStandalone, canInstall, promptInstall } = useIOSPWA();

const showPrompt = ref(false);
const updateAvailable = ref(false);
const dismissed = ref(false);

// Check if user has dismissed the prompt before
const checkDismissed = () => {
  const dismissedTime = localStorage.getItem('pwa-install-dismissed');
  if (dismissedTime) {
    const daysSinceDismissed = (Date.now() - parseInt(dismissedTime)) / (1000 * 60 * 60 * 24);
    // Show again after 7 days
    dismissed.value = daysSinceDismissed < 7;
  }
};

// Show prompt logic
const shouldShowPrompt = () => {
  if (dismissed.value || isStandalone.value) return false;
  
  // For iOS, show after user has visited 3 times
  if (isIOS.value) {
    const visits = parseInt(localStorage.getItem('app-visits') || '0') + 1;
    localStorage.setItem('app-visits', visits.toString());
    return visits >= 3;
  }
  
  // For others, show if install is available
  return canInstall.value;
};

const dismiss = () => {
  showPrompt.value = false;
  localStorage.setItem('pwa-install-dismissed', Date.now().toString());
};

const install = async () => {
  const installed = await promptInstall();
  if (installed) {
    showPrompt.value = false;
    // Track installation
    if ('gtag' in window) {
      (window as any).gtag('event', 'pwa_install', {
        event_category: 'engagement',
        event_label: 'prompt'
      });
    }
  }
};

const updateApp = () => {
  pwaService.skipWaiting();
};

// Event handlers
const handleUpdateAvailable = () => {
  updateAvailable.value = true;
  showPrompt.value = true;
};

const handleInstallPrompt = () => {
  if (shouldShowPrompt()) {
    // Delay showing prompt for better UX
    setTimeout(() => {
      showPrompt.value = true;
    }, 3000);
  }
};

onMounted(() => {
  checkDismissed();
  
  // Listen for PWA events
  window.addEventListener('pwa-update-available', handleUpdateAvailable);
  window.addEventListener('beforeinstallprompt', handleInstallPrompt);
  
  // Check if should show prompt
  if (shouldShowPrompt()) {
    setTimeout(() => {
      showPrompt.value = true;
    }, 5000); // Show after 5 seconds
  }
});

onUnmounted(() => {
  window.removeEventListener('pwa-update-available', handleUpdateAvailable);
  window.removeEventListener('beforeinstallprompt', handleInstallPrompt);
});
</script>

<style scoped>
.pwa-install-prompt {
  position: fixed;
  bottom: calc(20px + env(safe-area-inset-bottom, 0));
  left: 20px;
  right: 20px;
  max-width: 400px;
  margin: 0 auto;
  background: var(--background);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  animation: slide-up 0.3s ease-out;
  z-index: 1000;
}

@keyframes slide-up {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.install-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--border);
}

.install-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.install-header p {
  margin: 4px 0 0;
  font-size: 14px;
  color: var(--muted-foreground);
}

.close-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 20px;
  color: var(--muted-foreground);
  cursor: pointer;
  padding: 4px;
}

.app-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
}

.install-content {
  padding: 16px;
}

.install-steps {
  margin: 16px 0;
  padding-left: 0;
  list-style: none;
}

.install-steps li {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 14px;
}

.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--accent);
  color: var(--accent-foreground);
  border-radius: 8px;
  flex-shrink: 0;
}

.install-benefits {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.install-benefits h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.install-benefits ul {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.install-benefits li {
  font-size: 13px;
  margin-bottom: 4px;
  color: var(--muted-foreground);
}

.install-actions {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid var(--border);
}

.btn-primary,
.btn-secondary {
  flex: 1;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: var(--primary);
  color: var(--primary-foreground);
  border: none;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-secondary {
  background: transparent;
  color: var(--foreground);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--accent);
}

.update-prompt {
  padding: 16px;
  text-align: center;
}

.update-prompt p {
  margin: 0 0 12px;
  font-size: 14px;
}

/* iOS-specific styles */
.ios .pwa-install-prompt {
  border-radius: 16px;
}

.ios .install-steps {
  font-size: 15px;
}

/* Dark mode */
.dark .pwa-install-prompt {
  background: var(--card);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
</style>