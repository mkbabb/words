import { useStores } from '@/stores';

interface NavigationOptions {
    scrollOffset?: number;
    behavior?: ScrollBehavior;
    /** Called before scrolling to ensure the target is rendered (for virtual windowing). */
    ensureTargetWindow?: (id: string) => void;
}

export function useSidebarNavigation(options: NavigationOptions = {}) {
    const { scrollOffset = 96, behavior = 'smooth' } = options;

    const scrollToElement = (id: string) => {
        options.ensureTargetWindow?.(id);

        const element = document.getElementById(id);
        if (!element) return;

        const elementRect = element.getBoundingClientRect();
        const bodyRect = document.body.getBoundingClientRect();
        const elementPosition = elementRect.top - bodyRect.top;
        const offsetPosition = elementPosition - scrollOffset;

        window.scrollTo({
            top: offsetPosition,
            behavior,
        });
    };

    const scrollToCluster = (clusterId: string) => {
        scrollToElement(clusterId);
    };

    const scrollToPartOfSpeech = (clusterId: string, partOfSpeech: string) => {
        scrollToElement(`${clusterId}-${partOfSpeech}`);
    };

    const getDefinitionsForPartOfSpeech = (clusterId: string, partOfSpeech: string) => {
        const { content } = useStores();
        const entry = content.currentEntry;
        if (!entry?.definitions) return [];

        return entry.definitions
            .filter((def) => {
                const defCluster = def.meaning_cluster?.slug || def.meaning_cluster?.id || 'default';
                return defCluster === clusterId && def.part_of_speech === partOfSpeech;
            })
            .sort((a, b) => (b.relevancy || 1.0) - (a.relevancy || 1.0));
    };

    return {
        scrollToCluster,
        scrollToPartOfSpeech,
        scrollToElement,
        getDefinitionsForPartOfSpeech,
    };
}
