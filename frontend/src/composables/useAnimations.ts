import { ref } from 'vue';
import { useAppStore } from '@/stores';

export function useAnimations() {
  const store = useAppStore();
  const isAnimating = ref(false);

  // Search bar animation state
  const searchBarMoved = ref(false);
  const logoScaled = ref(false);

  // Animate search bar from center to top
  const animateSearchToTop = async () => {
    if (isAnimating.value) return;
    
    isAnimating.value = true;
    
    // Start animations
    searchBarMoved.value = true;
    logoScaled.value = true;
    
    // Wait for animation to complete
    await new Promise(resolve => setTimeout(resolve, 600));
    
    isAnimating.value = false;
  };

  // Reset search bar to center
  const resetSearchToCenter = async () => {
    if (isAnimating.value) return;
    
    isAnimating.value = true;
    
    // Reset animations
    searchBarMoved.value = false;
    logoScaled.value = false;
    
    // Wait for animation to complete
    await new Promise(resolve => setTimeout(resolve, 600));
    
    isAnimating.value = false;
  };

  // Smooth scroll to element
  const scrollToElement = (elementId: string) => {
    const element = document.getElementById(elementId);
    if (element) {
      element.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  };

  // Page transition effects
  const transitionToResults = async () => {
    if (!store.hasSearched) {
      await animateSearchToTop();
    }
  };

  // Reset to landing page
  const transitionToLanding = async () => {
    store.reset();
    await resetSearchToCenter();
  };

  return {
    isAnimating,
    searchBarMoved,
    logoScaled,
    animateSearchToTop,
    resetSearchToCenter,
    scrollToElement,
    transitionToResults,
    transitionToLanding,
  };
}