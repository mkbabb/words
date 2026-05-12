// Project-specific virtual scrolling (not in glass-ui)
export {
    useVirtualGrid,
    type UseVirtualGridOptions,
} from './useVirtualGrid';

// Section windowing — transposed from glass-ui v0.9.4 (retired at v1.0;
// see MIGRATION.md §§3.2-3.4 and docs/tranches/M/audit/W0-Lane-III-*.md).
export { useVirtualSectionWindow } from './useVirtualSectionWindow';
export { useWindowedStore } from './useWindowedStore';
export {
    buildSectionLayout,
    findSectionOffset,
    resolveActiveSection,
    resolveSectionWindow,
    type FlatSection,
    type ForcedSectionWindowRange,
    type SectionLayout,
    type SectionWindowRange,
} from './virtualSectionLayout';
