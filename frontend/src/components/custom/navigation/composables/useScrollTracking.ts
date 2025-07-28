import { ref, onMounted, onUnmounted, watch, type Ref } from 'vue';
import { useScroll, useThrottleFn } from '@vueuse/core';

interface TrackedElement {
    id: string;
    level: number; // 0 = cluster, 1 = part of speech, etc.
    parentId?: string;
    elements: Element[]; // Support multiple elements with same ID
    visibility: number;
}

interface UseScrollTrackingOptions {
    activeStates: Map<number, Ref<string>>; // level -> active ID ref
    rootMargin?: string;
    threshold?: number[];
    scrollDirectionBuffer?: number; // pixels to prevent rapid switching
}

export function useScrollTracking({
    activeStates,
    rootMargin = '-20% 0px -20% 0px', // Symmetric for consistency
    threshold = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
    scrollDirectionBuffer = 50
}: UseScrollTrackingOptions) {
    const trackedElements = new Map<string, TrackedElement>();
    const observer = ref<IntersectionObserver | null>(null);
    
    // Scroll state
    const { y } = useScroll(window);
    const lastScrollY = ref(0);
    const scrollDirection = ref<'up' | 'down' | 'idle'>('idle');
    const lastActiveUpdate = ref(0);
    
    // Track visibility scores for all elements
    const visibilityScores = new Map<string, number>();
    
    // Update scroll direction with hysteresis
    const updateScrollDirection = useThrottleFn(() => {
        const delta = y.value - lastScrollY.value;
        
        if (Math.abs(delta) < scrollDirectionBuffer) {
            scrollDirection.value = 'idle';
        } else if (delta > 0) {
            scrollDirection.value = 'down';
        } else {
            scrollDirection.value = 'up';
        }
        
        lastScrollY.value = y.value;
    }, 100);
    
    // Calculate element visibility score based on intersection ratio and position
    const calculateVisibilityScore = (entry: IntersectionObserverEntry): number => {
        const rect = entry.boundingClientRect;
        const viewportHeight = window.innerHeight;
        const centerY = rect.top + rect.height / 2;
        const viewportCenterY = viewportHeight / 2;
        
        // Score based on how close element center is to viewport center
        const centerDistance = Math.abs(centerY - viewportCenterY);
        const centerScore = 1 - (centerDistance / viewportCenterY);
        
        // Combine intersection ratio with center proximity
        return entry.intersectionRatio * 0.7 + Math.max(0, centerScore) * 0.3;
    };
    
    // Update active elements based on visibility
    const updateActiveElements = () => {
        const now = Date.now();
        
        // Prevent too frequent updates
        if (now - lastActiveUpdate.value < 50) return;
        lastActiveUpdate.value = now;
        
        // Group elements by level
        const elementsByLevel = new Map<number, TrackedElement[]>();
        
        for (const [id, score] of visibilityScores) {
            const element = trackedElements.get(id);
            if (!element || score <= 0) continue;
            
            element.visibility = score;
            
            if (!elementsByLevel.has(element.level)) {
                elementsByLevel.set(element.level, []);
            }
            elementsByLevel.get(element.level)!.push(element);
        }
        
        // Update active state for each level
        for (const [level, activeRef] of activeStates) {
            const elements = elementsByLevel.get(level) || [];
            
            if (elements.length === 0) continue;
            
            // Sort by visibility score
            elements.sort((a, b) => b.visibility - a.visibility);
            
            // Apply scroll direction bias
            if (scrollDirection.value !== 'idle' && elements.length > 1) {
                const currentActive = activeRef.value;
                const currentIndex = elements.findIndex(el => el.id === currentActive);
                
                // If scrolling down, prefer elements below current
                // If scrolling up, prefer elements above current
                if (currentIndex !== -1) {
                    const bias = scrollDirection.value === 'down' ? 0.1 : -0.1;
                    elements.forEach((el, idx) => {
                        if (scrollDirection.value === 'down' && idx > currentIndex) {
                            el.visibility += bias;
                        } else if (scrollDirection.value === 'up' && idx < currentIndex) {
                            el.visibility += bias;
                        }
                    });
                    
                    // Re-sort with bias applied
                    elements.sort((a, b) => b.visibility - a.visibility);
                }
            }
            
            // Only update if significantly more visible (hysteresis)
            const bestElement = elements[0];
            const currentActiveElement = elements.find(el => el.id === activeRef.value);
            
            if (!currentActiveElement || 
                bestElement.visibility > currentActiveElement.visibility + 0.15) {
                activeRef.value = bestElement.id;
                
                // Update parent levels if needed
                if (bestElement.parentId) {
                    const parentLevel = level - 1;
                    const parentRef = activeStates.get(parentLevel);
                    if (parentRef) {
                        parentRef.value = bestElement.parentId;
                    }
                }
            }
        }
    };
    
    // Set up intersection observer
    const setupObserver = () => {
        if (observer.value) {
            observer.value.disconnect();
        }
        
        observer.value = new IntersectionObserver(
            (entries) => {
                entries.forEach(entry => {
                    const id = entry.target.getAttribute('data-track-id');
                    if (!id) return;
                    
                    if (entry.isIntersecting) {
                        const score = calculateVisibilityScore(entry);
                        visibilityScores.set(id, score);
                    } else {
                        // Don't immediately remove, just set to 0
                        visibilityScores.set(id, 0);
                    }
                });
                
                updateActiveElements();
            },
            { rootMargin, threshold }
        );
    };
    
    // Register elements to track
    const trackElement = (element: Element, id: string, level: number, parentId?: string) => {
        if (!element.hasAttribute('data-track-id')) {
            element.setAttribute('data-track-id', id);
        }
        
        // If already tracking this ID, add to existing elements array
        const existing = trackedElements.get(id);
        if (existing) {
            if (!existing.elements.includes(element)) {
                existing.elements.push(element);
                if (observer.value) {
                    observer.value.observe(element);
                }
            }
        } else {
            trackedElements.set(id, { id, level, parentId, elements: [element], visibility: 0 });
            if (observer.value) {
                observer.value.observe(element);
            }
        }
    };
    
    // Untrack element
    const untrackElement = (id: string) => {
        const tracked = trackedElements.get(id);
        if (tracked && observer.value) {
            tracked.elements.forEach(el => observer.value!.unobserve(el));
        }
        trackedElements.delete(id);
        visibilityScores.delete(id);
    };
    
    // Handle special cases
    const handleEdgeCases = () => {
        const scrollHeight = document.documentElement.scrollHeight;
        const clientHeight = document.documentElement.clientHeight;
        
        // At top of page
        if (y.value <= 50) {
            // Find first element of each level
            for (const [level, activeRef] of activeStates) {
                const elements = Array.from(trackedElements.values())
                    .filter(el => el.level === level)
                    .sort((a, b) => {
                        const aTop = Math.min(...a.elements.map(e => e.getBoundingClientRect().top));
                        const bTop = Math.min(...b.elements.map(e => e.getBoundingClientRect().top));
                        return aTop - bTop;
                    });
                
                if (elements.length > 0) {
                    activeRef.value = elements[0].id;
                }
            }
        }
        
        // At bottom of page
        else if (y.value + clientHeight >= scrollHeight - 50) {
            // Find last element of each level
            for (const [level, activeRef] of activeStates) {
                const elements = Array.from(trackedElements.values())
                    .filter(el => el.level === level)
                    .sort((a, b) => {
                        const aTop = Math.max(...a.elements.map(e => e.getBoundingClientRect().top));
                        const bTop = Math.max(...b.elements.map(e => e.getBoundingClientRect().top));
                        return bTop - aTop;
                    });
                
                if (elements.length > 0) {
                    activeRef.value = elements[0].id;
                }
            }
        }
    };
    
    // Watch scroll position
    watch(y, () => {
        updateScrollDirection();
        handleEdgeCases();
    });
    
    onMounted(() => {
        setupObserver();
    });
    
    onUnmounted(() => {
        if (observer.value) {
            observer.value.disconnect();
        }
    });
    
    return {
        trackElement,
        untrackElement,
        scrollDirection,
        setupObserver,
        updateActiveElements
    };
}