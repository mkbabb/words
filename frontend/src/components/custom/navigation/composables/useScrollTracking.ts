import { ref, onMounted, onUnmounted, type Ref } from 'vue';
import { useDebounceFn } from '@vueuse/core';

interface TrackedElement {
    id: string;
    level: number; // 0 = cluster, 1 = part of speech
    parentId?: string;
    elements: Element[]; // DOM elements (can be multiple)
}

interface UseScrollTrackingOptions {
    activeStates: Map<number, Ref<string>>; // level -> active ID ref
    rootMargin?: string;
}

export function useScrollTracking({
    activeStates,
    rootMargin = '-40% 0px -60% 0px' // Creates a reading line at 40% from top
}: UseScrollTrackingOptions) {
    const trackedElements = new Map<string, TrackedElement>();
    const observer = ref<IntersectionObserver | null>(null);
    const previousActives = new Map<number, string>();
    
    // Elements currently in the reading zone
    const elementsInReadingZone = new Set<string>();
    
    // Last known scroll position
    let lastScrollY = 0;
    
    // Get all elements sorted by their position on the page
    const getSortedElements = (level?: number): Array<{id: string; element: TrackedElement; top: number}> => {
        const elements: Array<{id: string; element: TrackedElement; top: number}> = [];
        
        for (const [id, element] of trackedElements) {
            if (level !== undefined && element.level !== level) continue;
            
            // Get the topmost position of all instances
            const tops = element.elements.map(el => el.getBoundingClientRect().top);
            if (tops.length === 0) continue;
            
            elements.push({
                id,
                element,
                top: Math.min(...tops)
            });
        }
        
        return elements.sort((a, b) => a.top - b.top);
    };
    
    // Update active elements - the core logic
    const updateActiveElementsRaw = () => {
        const scrollTop = window.scrollY;
        const scrollBottom = scrollTop + window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;
        
        // Check if we're at the edges
        const isAtTop = scrollTop < 50;
        const isAtBottom = scrollBottom >= documentHeight - 50;
        
        // Update each level
        for (const [level, activeRef] of activeStates) {
            const sortedElements = getSortedElements(level);
            if (sortedElements.length === 0) continue;
            
            let newActive: string | null = null;
            
            // Edge case: at top of page
            if (isAtTop) {
                newActive = sortedElements[0].id;
            }
            // Edge case: at bottom of page
            else if (isAtBottom) {
                newActive = sortedElements[sortedElements.length - 1].id;
            }
            // Normal case: find the topmost element in reading zone
            else {
                // Get elements in reading zone, sorted by position
                const inZone = sortedElements.filter(item => 
                    elementsInReadingZone.has(item.id)
                );
                
                if (inZone.length > 0) {
                    // Always use the topmost element in the reading zone
                    newActive = inZone[0].id;
                } else {
                    // Keep previous if nothing in zone
                    newActive = previousActives.get(level) || null;
                }
            }
            
            // Only update if there's a valid new active and it's different
            if (newActive && newActive !== activeRef.value) {
                activeRef.value = newActive;
                previousActives.set(level, newActive);
                
                // Update parent cluster when part of speech changes
                if (level === 1) {
                    const element = trackedElements.get(newActive);
                    if (element?.parentId) {
                        const parentRef = activeStates.get(0);
                        if (parentRef && parentRef.value !== element.parentId) {
                            parentRef.value = element.parentId;
                            previousActives.set(0, element.parentId);
                        }
                    }
                }
            }
        }
    };
    
    // Debounced version to prevent jitter
    const updateActiveElements = useDebounceFn(updateActiveElementsRaw, 150);
    
    // Set up intersection observer
    const setupObserver = () => {
        if (observer.value) {
            observer.value.disconnect();
        }
        
        observer.value = new IntersectionObserver(
            (entries) => {
                let hasChanges = false;
                
                entries.forEach(entry => {
                    const id = entry.target.getAttribute('data-track-id');
                    if (!id) return;
                    
                    if (entry.isIntersecting) {
                        if (!elementsInReadingZone.has(id)) {
                            elementsInReadingZone.add(id);
                            hasChanges = true;
                        }
                    } else {
                        if (elementsInReadingZone.delete(id)) {
                            hasChanges = true;
                        }
                    }
                });
                
                if (hasChanges) {
                    updateActiveElements();
                }
            },
            { rootMargin, threshold: 0 }
        );
    };
    
    // Register element for tracking
    const trackElement = (element: Element, id: string, level: number, parentId?: string) => {
        if (!element.hasAttribute('data-track-id')) {
            element.setAttribute('data-track-id', id);
        }
        
        const existing = trackedElements.get(id);
        if (existing) {
            if (!existing.elements.includes(element)) {
                existing.elements.push(element);
                observer.value?.observe(element);
            }
        } else {
            trackedElements.set(id, { 
                id, 
                level, 
                parentId, 
                elements: [element] 
            });
            observer.value?.observe(element);
        }
    };
    
    // Untrack element
    const untrackElement = (id: string) => {
        const tracked = trackedElements.get(id);
        if (tracked && observer.value) {
            tracked.elements.forEach(el => observer.value!.unobserve(el));
        }
        trackedElements.delete(id);
        elementsInReadingZone.delete(id);
    };
    
    // Check scroll position periodically for edge cases
    let scrollCheckInterval: number | null = null;
    
    onMounted(() => {
        // Check scroll position every 200ms
        scrollCheckInterval = window.setInterval(() => {
            const currentScrollY = window.scrollY;
            if (Math.abs(currentScrollY - lastScrollY) > 50) {
                lastScrollY = currentScrollY;
                updateActiveElements();
            }
        }, 200);
        setupObserver();
    });
    
    onUnmounted(() => {
        observer.value?.disconnect();
        if (scrollCheckInterval) {
            clearInterval(scrollCheckInterval);
        }
    });
    
    return {
        trackElement,
        untrackElement,
        setupObserver,
        updateActiveElements
    };
}