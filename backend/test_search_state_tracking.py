#!/usr/bin/env python3
"""Test script to demonstrate search pipeline state tracking integration."""

import asyncio
import json
from floridify.core.search_pipeline import search_word_pipeline
from floridify.models.pipeline_state import StateTracker, PipelineState
from floridify.constants import Language


async def track_search_progress(word: str):
    """Demonstrate search pipeline with state tracking."""
    print(f"\n🔍 Searching for: '{word}'")
    print("=" * 60)
    
    # Create state tracker
    state_tracker = StateTracker()
    
    # Task to collect state updates
    async def collect_states():
        states = []
        async for state in state_tracker.get_state_updates():
            states.append(state)
            # Print progress bar
            progress_pct = int(state.progress * 100)
            bar_length = 40
            filled = int(bar_length * state.progress)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            print(f"\r[{bar}] {progress_pct:3d}% - {state.stage}: {state.message}", end="")
            
            if state.metadata:
                print(f"\n  📊 Metadata: {json.dumps(state.metadata, indent=2)}")
            
            if state.data and "partial_results" in state.data:
                print(f"  📝 Found {len(state.data['partial_results'])} partial results")
            
            # Break on completion or error
            if state.stage in ("completed", "error"):
                print()  # New line after progress
                break
                
        return states
    
    # Start collecting states in background
    state_task = asyncio.create_task(collect_states())
    
    # Perform search with state tracking
    results = await search_word_pipeline(
        word=word,
        languages=[Language.ENGLISH],
        semantic=False,  # Disabled for faster demo
        max_results=10,
        normalize=True,
        state_tracker=state_tracker,
    )
    
    # Wait for all states to be collected
    collected_states = await state_task
    
    # Display results
    print(f"\n✅ Search Results: {len(results)} found")
    for i, result in enumerate(results[:5], 1):
        print(f"  {i}. {result.word} (score: {result.score:.3f}, method: {result.method.value})")
    
    # Display performance summary
    if collected_states:
        final_state = collected_states[-1]
        if final_state.metadata and "pipeline_time_ms" in final_state.metadata:
            print(f"\n⏱️  Total Pipeline Time: {final_state.metadata['pipeline_time_ms']}ms")
        
        # Show method breakdown
        for state in collected_states:
            if state.metadata and "method_times_ms" in state.metadata:
                print("\n📊 Method Performance Breakdown:")
                for method, time_ms in state.metadata["method_times_ms"].items():
                    print(f"  - {method}: {time_ms}ms")
                break
    
    return results, collected_states


async def main():
    """Run test demonstrations."""
    test_words = [
        "hello",           # Simple word
        "world",          # Another simple word
        "extraordinaire", # Longer word
        "typo",          # Will test fuzzy search
        "machine learning",  # Phrase (if supported)
    ]
    
    for word in test_words:
        try:
            await track_search_progress(word)
            await asyncio.sleep(0.5)  # Brief pause between searches
        except Exception as e:
            print(f"\n❌ Error searching for '{word}': {e}")


if __name__ == "__main__":
    asyncio.run(main())