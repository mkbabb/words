import { describe, it, expect } from 'vitest';
import { useWindowedStore } from '../useWindowedStore';

/** Helper: generate items [offset..offset+count) */
function items(offset: number, count: number): { id: number; word: string }[] {
    return Array.from({ length: count }, (_, i) => ({
        id: offset + i,
        word: `word-${offset + i}`,
    }));
}

describe('useWindowedStore', () => {
    // ─── Basic operations ─────────────────────────────────────────

    it('starts empty', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        expect(store.items.value).toEqual([]);
        expect(store.windowStart.value).toBe(0);
    });

    it('set(replace=true) resets window', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        store.set(items(0, 5), true);
        expect(store.items.value).toHaveLength(5);
        expect(store.windowStart.value).toBe(0);
        expect(store.items.value[0].id).toBe(0);
        expect(store.items.value[4].id).toBe(4);
    });

    it('set(replace=false) appends', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 20 });
        store.set(items(0, 5), true);
        store.set(items(5, 5), false);
        expect(store.items.value).toHaveLength(10);
        expect(store.windowStart.value).toBe(0);
        expect(store.items.value[0].id).toBe(0);
        expect(store.items.value[9].id).toBe(9);
    });

    it('clear() resets everything', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        store.set(items(0, 5), true);
        store.clear();
        expect(store.items.value).toEqual([]);
        expect(store.windowStart.value).toBe(0);
    });

    // ─── Forward eviction ─────────────────────────────────────────

    it('evicts from front when appending past maxResident', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        store.set(items(0, 8), true);       // [0..7], ws=0
        store.set(items(8, 5), false);      // merged [0..12] = 13 items, trim 3
        expect(store.items.value).toHaveLength(10);
        expect(store.windowStart.value).toBe(3);
        expect(store.items.value[0].id).toBe(3);   // first item is id=3
        expect(store.items.value[9].id).toBe(12);   // last item is id=12
    });

    it('windowStart accumulates across multiple evictions', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        store.set(items(0, 10), true);      // [0..9], ws=0
        store.set(items(10, 5), false);     // trim 5 → ws=5, items=[5..14]
        store.set(items(15, 5), false);     // trim 5 → ws=10, items=[10..19]
        expect(store.windowStart.value).toBe(10);
        expect(store.items.value[0].id).toBe(10);
        expect(store.items.value[9].id).toBe(19);
    });

    // ─── Backward (prepend) ───────────────────────────────────────

    it('prepend adds items before the window', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 20 });
        store.set(items(10, 5), true);      // [10..14], ws=0
        store.windowStart.value = 10;       // manually set ws to simulate eviction
        store.prepend(items(5, 5), 5);      // prepend [5..9], ws=5
        expect(store.windowStart.value).toBe(5);
        expect(store.items.value).toHaveLength(10);
        expect(store.items.value[0].id).toBe(5);
        expect(store.items.value[9].id).toBe(14);
    });

    it('prepend evicts from end when over maxResident', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        store.set(items(10, 8), true);      // [10..17], ws=0
        store.windowStart.value = 10;
        store.prepend(items(5, 5), 5);      // prepend [5..9] + [10..17] = 13, trim to 10
        expect(store.windowStart.value).toBe(5);
        expect(store.items.value).toHaveLength(10);
        expect(store.items.value[0].id).toBe(5);
        expect(store.items.value[9].id).toBe(14);  // items 15-17 evicted from end
    });

    // ─── Pathological scrolling scenarios ─────────────────────────

    it('scenario: scroll down, evict, scroll back to top', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });

        // Load initial page
        store.set(items(0, 5), true);       // [0..4], ws=0

        // Scroll down: load more pages until eviction
        store.set(items(5, 5), false);      // [0..9], ws=0
        store.set(items(10, 5), false);     // [0..14]=15, trim 5 → ws=5, [5..14]

        expect(store.windowStart.value).toBe(5);
        expect(store.items.value[0].id).toBe(5);

        // Scroll back to top: reset window from offset 0
        store.set(items(0, 10), true);      // replace → [0..9], ws=0
        // Manually set windowStart to 0 (as loadBeforeWordlist does)
        // (set with replace=true already does this)

        expect(store.windowStart.value).toBe(0);
        expect(store.items.value[0].id).toBe(0);
        expect(store.items.value[9].id).toBe(9);
    });

    it('scenario: rapid forward scroll (multiple appends)', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });
        store.set(items(0, 5), true);

        // Simulate rapid loadMore calls
        for (let page = 1; page < 20; page++) {
            store.set(items(page * 5, 5), false);
        }

        // Should have last 10 items, windowStart advanced
        expect(store.items.value).toHaveLength(10);
        const lastId = store.items.value[9].id;
        expect(lastId).toBe(99); // 20 pages × 5 = 100, last is 99
        expect(store.items.value[0].id).toBe(90);
        expect(store.windowStart.value).toBe(90);
    });

    it('scenario: zigzag scroll (forward, back, forward, back)', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });

        // Forward: load pages 0-2
        store.set(items(0, 5), true);
        store.set(items(5, 5), false);
        store.set(items(10, 5), false);     // eviction: ws=5, [5..14]

        // Back: reset to page 0
        store.set(items(0, 10), true);      // ws=0, [0..9]
        expect(store.windowStart.value).toBe(0);
        expect(store.items.value[0].id).toBe(0);

        // Forward again
        store.set(items(10, 5), false);     // [0..14]=15, trim 5 → ws=5, [5..14]
        expect(store.windowStart.value).toBe(5);

        // Back again: reset to page 0
        store.set(items(0, 10), true);
        expect(store.windowStart.value).toBe(0);
        expect(store.items.value[0].id).toBe(0);
    });

    it('scenario: data continuity — items are contiguous after forward scroll', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 50 });

        // Load 5 pages of 10
        for (let page = 0; page < 5; page++) {
            store.set(items(page * 10, 10), page === 0);
        }

        // Verify contiguity: each item's id should be exactly 1 more than the previous
        for (let i = 1; i < store.items.value.length; i++) {
            expect(store.items.value[i].id).toBe(store.items.value[i - 1].id + 1);
        }
    });

    it('scenario: data continuity — items are contiguous after backward reset', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });

        // Forward to cause eviction
        store.set(items(0, 10), true);
        store.set(items(10, 10), false);    // evicts [0..9], ws=10, items=[10..19]

        // Backward reset to offset 5
        store.set(items(5, 10), true);
        store.windowStart.value = 5;

        // Verify contiguity
        for (let i = 1; i < store.items.value.length; i++) {
            expect(store.items.value[i].id).toBe(store.items.value[i - 1].id + 1);
        }
        expect(store.items.value[0].id).toBe(5);
    });

    // ─── Bug: forward append after backward reset ─────────────────

    it('appendIfCurrent rejects stale appends after reset', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });

        // 1. Load initial page
        store.set(items(0, 5), true);           // gen=1, ws=0, [0..4]
        const genBeforeReset = store.generation.value;

        // 2. Scroll forward
        store.set(items(5, 5), false);          // ws=0, [0..9]
        store.set(items(10, 5), false);         // ws=5, [5..14]

        // 3. Backward reset (simulates loadBeforeWordlist)
        store.set(items(0, 10), true);          // gen=2, ws=0, [0..9]

        // 4. Stale forward append with OLD generation — should be REJECTED
        const accepted = store.appendIfCurrent(items(15, 5), genBeforeReset);
        expect(accepted).toBe(false);

        // Items should still be [0..9], no gap
        const ids = store.items.value.map(i => i.id);
        expect(ids).toEqual([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
        expect(store.windowStart.value).toBe(0);
    });

    it('appendIfCurrent accepts current-generation appends', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 20 });
        store.set(items(0, 5), true);           // gen=1
        const currentGen = store.generation.value;

        const accepted = store.appendIfCurrent(items(5, 5), currentGen);
        expect(accepted).toBe(true);
        expect(store.items.value).toHaveLength(10);
        expect(store.items.value[9].id).toBe(9);
    });

    it('BUG REPRO: concurrent forward load during backward reset', () => {
        const store = useWindowedStore<{ id: number; word: string }>({ maxResident: 10 });

        // Load initial data
        store.set(items(0, 10), true);

        // Forward scroll causes eviction
        store.set(items(10, 5), false);     // ws=5, [5..14]
        store.set(items(15, 5), false);     // ws=10, [10..19]

        // User scrolls back to top — backward reset
        store.set(items(0, 10), true);
        store.windowStart.value = 0;        // simulate setWindowStart

        // Verify we're clean at offset 0
        expect(store.windowStart.value).toBe(0);
        expect(store.items.value[0].id).toBe(0);
        expect(store.items.value[9].id).toBe(9);

        // Forward scroll resumes from the new window
        store.set(items(10, 5), false);     // append [10..14] → [0..14]

        // Now all items should be contiguous
        const ids = store.items.value.map(i => i.id);
        for (let i = 1; i < ids.length; i++) {
            expect(ids[i]).toBe(ids[i - 1] + 1);
        }
    });
});
