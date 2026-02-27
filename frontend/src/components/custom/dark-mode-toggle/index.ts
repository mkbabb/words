export { default as DarkModeToggle } from './DarkModeToggle.vue';

import { computed } from 'vue';
import { useUIStore } from '@/stores/ui/ui-state';

// Unified theme: UIStore is the single source of truth
// isDark is a computed that reads from UIStore's resolvedTheme
const isDark = computed(() => {
  const ui = useUIStore();
  return ui.resolvedTheme === 'dark';
});

export const changeTheme = () => {
  const ui = useUIStore();
  ui.toggleTheme();
};

export { isDark };
