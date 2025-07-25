#!/usr/bin/env python
"""Test audio synthesis for pronunciations."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floridify.audio import AudioSynthesizer
from floridify.models import Pronunciation, Word
from floridify.storage.mongodb import init_database
from floridify.utils.logging import setup_logging


async def test_audio_synthesis():
    """Test audio synthesis with the word 'example'."""
    setup_logging(verbose=True)
    
    # Initialize database
    await init_database()
    
    # Create a test word
    word = Word(
        text="example",
        language="en",
    )
    await word.save()
    
    # Create a test pronunciation with IPA
    pronunciation = Pronunciation(
        word_id=str(word.id),
        phonetic="ig-ZAM-pul",
        ipa_american="/ɪɡˈzæmpəl/",
        ipa_british="/ɪɡˈzɑːmpəl/",
        syllables=["ex", "am", "ple"],
        stress_pattern="0-1-0",  # Secondary-Primary-Unstressed
    )
    await pronunciation.save()
    
    print(f"Created test word: {word.text}")
    print(f"Created pronunciation: {pronunciation.phonetic}")
    print(f"  American IPA: {pronunciation.ipa_american}")
    print(f"  British IPA: {pronunciation.ipa_british}")
    
    # Test audio synthesis
    try:
        synthesizer = AudioSynthesizer()
        print("\nTesting audio synthesis...")
        
        # Generate audio files
        audio_files = await synthesizer.synthesize_pronunciation(
            pronunciation, word.text
        )
        
        if audio_files:
            print(f"\nSuccessfully generated {len(audio_files)} audio files:")
            for audio in audio_files:
                print(f"  - {audio.accent} accent: {audio.url}")
                print(f"    Format: {audio.format}, Size: {audio.size_bytes} bytes")
                print(f"    Duration: {audio.duration_ms}ms")
                
            # Update pronunciation with audio file IDs
            pronunciation.audio_file_ids = [str(audio.id) for audio in audio_files]
            await pronunciation.save()
            print(f"\nUpdated pronunciation with audio file IDs: {pronunciation.audio_file_ids}")
        else:
            print("\nNo audio files were generated.")
            
    except Exception as e:
        print(f"\nError during audio synthesis: {e}")
        import traceback
        traceback.print_exc()
        
    # Clean up test data
    print("\nCleaning up test data...")
    await pronunciation.delete()
    await word.delete()
    for audio in audio_files:
        await audio.delete()
    
    print("Test complete!")


if __name__ == "__main__":
    asyncio.run(test_audio_synthesis())