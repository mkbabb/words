/** Minimal interface for tree-structured content with scroll targets. */
export interface TreeNode {
    id: string;
    children?: TreeNode[];
}

/** Flat index entry for a tree node. */
export interface TreeIndexEntry<T extends TreeNode = TreeNode> {
    node: T;
    depth: number;
    /** ID of the root-level ancestor (self.id when depth === 0). */
    rootId: string;
    /** Direct parent ID (null for root nodes). */
    parentId: string | null;
    /** Index within root-level nodes. */
    rootIndex: number;
}

/** Options for scroll tracking. */
export interface ScrollTrackerOptions {
    /** IntersectionObserver rootMargin. Default: "-20% 0px -60% 0px" */
    rootMargin?: string;
    threshold?: number;
}
