#!/usr/bin/env python3
"""Direct test of Wiktionary pronunciation extraction."""

import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from floridify.connectors.wiktionary import WiktionaryConnector
import wikitextparser as wtp


async def test_pronunciation_extraction():
    """Test the pronunciation extraction directly."""
    
    # Sample wikitext with pronunciation
    wikitext = """==English==
===Pronunciation===
* {{IPA|en|/ɪɡˈzɑːm.pəl/|a=RP}}
* {{IPA|en|/ɪɡˈzam.pəl/|a=Northern England,Scotland}}
* {{IPA|en|/ɪɡˈzæm.pəl/|[ɪɡˈzɛəmpəɫ]|a=US}}
* {{audio|en|en-us-example.ogg|a=US}}
* {{IPA|en|/əɡˈzæm.pəl/|a=US,Australia,weak vowel}}
"""
    
    # Create connector
    connector = WiktionaryConnector()
    
    # Parse wikitext - need to get the first section
    parsed = wtp.parse(wikitext)
    
    # Create a mock section object since _extract_pronunciation expects a Section
    class MockSection:
        def __init__(self, content):
            self.sections = []
            self.content = content
            
        def __str__(self):
            return self.content
    
    section = MockSection(wikitext)
    
    # Extract pronunciation
    pronunciation = connector._extract_pronunciation(section, "test_word_id")
    
    if pronunciation:
        print(f"✓ Pronunciation extracted:")
        print(f"  Phonetic: {pronunciation.phonetic}")
        print(f"  IPA: {pronunciation.ipa_american}")
        
        # Validate
        if pronunciation.phonetic and '.ogg' in pronunciation.phonetic:
            print("❌ ERROR: Phonetic contains audio file reference!")
        else:
            print("✓ Phonetic is clean")
            
        if pronunciation.ipa_american:
            print("✓ IPA extracted successfully")
        else:
            print("❌ ERROR: IPA not extracted")
    else:
        print("❌ ERROR: No pronunciation extracted")
    
    await connector.close()


if __name__ == "__main__":
    asyncio.run(test_pronunciation_extraction())