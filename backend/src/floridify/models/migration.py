"""Data model migration utilities."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from ..constants import DictionaryProvider, Language
from .base import ModelInfo
from .models import (
    Definition as LegacyDefinition,
)
from .models import (
    DictionaryEntry as LegacyDictionaryEntry,
)
from .models import (
    SynthesizedDictionaryEntry as LegacySynthesizedDictionaryEntry,
)
from .models_v2 import (
    Definition,
    Example,
    Fact,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    Word,
)
from .relationships import MeaningCluster


class MigrationStats(BaseModel):
    """Track migration progress."""
    
    words_created: int = 0
    definitions_created: int = 0
    examples_created: int = 0
    pronunciations_created: int = 0
    facts_created: int = 0
    errors: list[str] = []


async def migrate_legacy_entry(
    legacy_entry: LegacyDictionaryEntry,
    stats: MigrationStats
) -> Word:
    """Migrate a legacy DictionaryEntry to new Word model."""
    
    try:
        # Create Word document
        word = Word(
            text=legacy_entry.word,
            normalized=legacy_entry.word.lower(),
            language=Language.ENGLISH,
            word_forms=[],  # Extract from definitions if available
            offensive_flag=False,
        )
        await word.save()
        stats.words_created += 1
        
        # Migrate pronunciation
        if legacy_entry.pronunciation:
            pronunciation = Pronunciation(
                word_id=str(word.id),
                phonetic=legacy_entry.pronunciation.phonetic,
                ipa_american=legacy_entry.pronunciation.ipa,
                syllables=[],
                stress_pattern=None,
            )
            await pronunciation.save()
            stats.pronunciations_created += 1
        
        # Migrate provider data and definitions
        for provider_name, provider_data in legacy_entry.provider_data.items():
            # Create new provider data
            new_provider_data = ProviderData(
                word_id=str(word.id),
                provider=DictionaryProvider(provider_name),
                definition_ids=[],
                pronunciation_id=str(pronunciation.id) if pronunciation else None,
                etymology=None,  # Extract if available
                raw_data=provider_data.raw_metadata,
            )
            
            # Migrate definitions
            for legacy_def in provider_data.definitions:
                definition = await migrate_legacy_definition(
                    legacy_def, str(word.id), provider_name, stats
                )
                new_provider_data.definition_ids.append(str(definition.id))
            
            await new_provider_data.save()
        
        return word
        
    except Exception as e:
        stats.errors.append(f"Error migrating {legacy_entry.word}: {str(e)}")
        raise


async def migrate_legacy_definition(
    legacy_def: LegacyDefinition,
    word_id: str,
    provider_name: str,
    stats: MigrationStats
) -> Definition:
    """Migrate a legacy Definition to new model."""
    
    # Create meaning cluster from legacy data
    meaning_cluster = MeaningCluster(
        id=legacy_def.meaning_cluster or "default",
        name=legacy_def.meaning_cluster or "Primary",
        description=legacy_def.definition[:50] + "...",
        order=0,
        relevance=legacy_def.relevancy or 0.5,
    )
    
    # Create definition
    definition = Definition(
        word_id=word_id,
        part_of_speech=legacy_def.word_type,
        text=legacy_def.definition,
        meaning_cluster=meaning_cluster,
        synonyms=legacy_def.synonyms,
        antonyms=[],
        example_ids=[],
        provider_data_id=None,  # Will be set by provider data
        frequency_band=None,  # Will be enhanced later
    )
    await definition.save()
    stats.definitions_created += 1
    
    # Migrate examples
    for gen_example in legacy_def.examples.generated:
        example = Example(
            definition_id=str(definition.id),
            text=gen_example.sentence,
            type="generated",
            model_info=ModelInfo(
                name=legacy_def.source_attribution or "unknown",
                generation_count=1,
                confidence=legacy_def.quality_score or 0.8,
            ),
        )
        await example.save()
        definition.example_ids.append(example.id)
        stats.examples_created += 1
    
    for lit_example in legacy_def.examples.literature:
        example = Example(
            definition_id=str(definition.id),
            text=lit_example.sentence,
            type="literature",
            source=lit_example.source,
        )
        await example.save()
        definition.example_ids.append(example.id)
        stats.examples_created += 1
    
    # Update definition with example IDs
    await definition.save()
    
    return definition


async def migrate_synthesized_entry(
    legacy_synth: LegacySynthesizedDictionaryEntry,
    word_id: str,
    stats: MigrationStats
) -> SynthesizedDictionaryEntry:
    """Migrate a legacy synthesized entry."""
    
    try:
        # Get pronunciation ID if exists
        pronunciation = await Pronunciation.find_one(Pronunciation.word_id == word_id)
        
        # Collect definition IDs
        definition_ids = []
        for legacy_def in legacy_synth.definitions:
            definition = await migrate_legacy_definition(
                legacy_def, word_id, "synthesis", stats
            )
            definition_ids.append(definition.id)
        
        # Migrate facts
        fact_ids = []
        for legacy_fact in legacy_synth.facts:
            fact = Fact(
                word_id=word_id,
                content=legacy_fact.content,
                category=legacy_fact.category,
                model_info=ModelInfo(
                    name=legacy_synth.model or "gpt-4",
                    generation_count=1,
                    confidence=legacy_fact.confidence,
                ),
            )
            await fact.save()
            fact_ids.append(str(fact.id))
            stats.facts_created += 1
        
        # Create synthesized entry
        synth_entry = SynthesizedDictionaryEntry(
            word_id=word_id,
            pronunciation_id=str(pronunciation.id) if pronunciation else None,
            definition_ids=definition_ids,
            etymology=None,  # Extract if available
            fact_ids=fact_ids,
            model_info=ModelInfo(
                name=legacy_synth.model or "gpt-4",
                generation_count=1,
                confidence=legacy_synth.confidence or 0.8,
            ),
            source_provider_data_ids=[],  # Link to provider data
        )
        await synth_entry.save()
        
        return synth_entry
        
    except Exception as e:
        stats.errors.append(f"Error migrating synthesis for word {word_id}: {str(e)}")
        raise


async def run_migration(db_url: str = "mongodb://localhost:27017/floridify") -> None:
    """Run the complete migration."""
    
    # Initialize database
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(db_url)
    db = cast(AsyncIOMotorDatabase[Any], client.floridify)
    
    # Initialize Beanie with all models
    await init_beanie(
        database=db,
        document_models=[
            # Legacy models
            LegacyDictionaryEntry,
            LegacySynthesizedDictionaryEntry,
            # New models
            Word,
            Definition,
            Example,
            Fact,
            Pronunciation,
            ProviderData,
            SynthesizedDictionaryEntry,
        ]
    )
    
    stats = MigrationStats()
    
    print("Starting migration...")
    
    # Migrate dictionary entries
    async for legacy_entry in LegacyDictionaryEntry.find_all():
        try:
            word = await migrate_legacy_entry(legacy_entry, stats)
            print(f"Migrated word: {word.text}")
        except Exception as e:
            print(f"Failed to migrate {legacy_entry.word}: {e}")
    
    # Migrate synthesized entries
    async for legacy_synth in LegacySynthesizedDictionaryEntry.find_all():
        try:
            # Find corresponding word
            word = await Word.find_one(Word.text == legacy_synth.word)
            if word:
                await migrate_synthesized_entry(legacy_synth, word.id, stats)
                print(f"Migrated synthesis for: {word.text}")
        except Exception as e:
            print(f"Failed to migrate synthesis for {legacy_synth.word}: {e}")
    
    print("\nMigration complete!")
    print(f"Words created: {stats.words_created}")
    print(f"Definitions created: {stats.definitions_created}")
    print(f"Examples created: {stats.examples_created}")
    print(f"Pronunciations created: {stats.pronunciations_created}")
    print(f"Facts created: {stats.facts_created}")
    print(f"Errors: {len(stats.errors)}")
    
    if stats.errors:
        print("\nErrors:")
        for error in stats.errors[:10]:
            print(f"  - {error}")


if __name__ == "__main__":
    asyncio.run(run_migration())