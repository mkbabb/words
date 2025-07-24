"""Tests for enhanced data models."""

import pytest
from datetime import datetime
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from floridify.models import (
    Word,
    Definition,
    Example,
    Fact,
    Pronunciation,
    ProviderData,
    SynthesizedDictionaryEntry,
    MeaningCluster,
    ModelInfo,
    Etymology,
)
from floridify.constants import Language, DictionaryProvider


@pytest.fixture
async def db():
    """Initialize test database."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.test_floridify
    
    await init_beanie(
        database=db,
        document_models=[
            Word, Definition, Example, Fact, Pronunciation,
            ProviderData, SynthesizedDictionaryEntry
        ]
    )
    
    yield db
    
    # Cleanup
    await client.drop_database("test_floridify")
    client.close()


@pytest.mark.asyncio
async def test_word_creation(db):
    """Test Word document creation with foreign keys."""
    word = Word(
        text="test",
        normalized="test",
        language=Language.ENGLISH,
    )
    await word.save()
    
    assert word.id is not None
    assert word.created_at is not None
    assert word.version == 1
    
    # Retrieve and verify
    retrieved = await Word.find_one(Word.text == "test")
    assert retrieved is not None
    assert retrieved.text == "test"


@pytest.mark.asyncio
async def test_definition_with_examples(db):
    """Test Definition with Example foreign keys."""
    # Create word first
    word = Word(text="run", normalized="run", language=Language.ENGLISH)
    await word.save()
    
    # Create definition
    definition = Definition(
        word_id=word.id,
        part_of_speech="verb",
        text="to move quickly",
        meaning_cluster=MeaningCluster(
            id="run_movement",
            name="Movement sense",
            description="Physical movement",
            order=0,
            relevance=0.9
        ),
        synonyms=["sprint", "dash"],
        example_ids=[]
    )
    await definition.save()
    
    # Create examples
    example1 = Example(
        definition_id=definition.id,
        text="She runs every morning",
        type="generated",
        model_info=ModelInfo(
            name="gpt-4",
            confidence=0.95,
            generation_count=1
        )
    )
    await example1.save()
    
    # Update definition with example ID
    definition.example_ids.append(example1.id)
    await definition.save()
    
    # Verify relationships
    assert len(definition.example_ids) == 1
    retrieved_example = await Example.get(example1.id)
    assert retrieved_example.definition_id == definition.id


@pytest.mark.asyncio
async def test_provider_data_structure(db):
    """Test ProviderData with foreign keys."""
    word = Word(text="hello", normalized="hello", language=Language.ENGLISH)
    await word.save()
    
    # Create pronunciation
    pronunciation = Pronunciation(
        word_id=word.id,
        phonetic="heh-LOH",
        ipa_american="/həˈloʊ/",
        syllables=["hel", "lo"]
    )
    await pronunciation.save()
    
    # Create provider data
    provider_data = ProviderData(
        word_id=word.id,
        provider=DictionaryProvider.WIKTIONARY,
        definition_ids=[],
        pronunciation_id=pronunciation.id,
        etymology=Etymology(
            text="From Old English",
            origin_language="Old English",
            root_words=["hǣl"],
        )
    )
    await provider_data.save()
    
    assert provider_data.pronunciation_id == pronunciation.id
    assert provider_data.etymology.origin_language == "Old English"


@pytest.mark.asyncio
async def test_synthesized_entry_provenance(db):
    """Test SynthesizedDictionaryEntry with complete provenance."""
    word = Word(text="example", normalized="example", language=Language.ENGLISH)
    await word.save()
    
    # Create components
    pronunciation = Pronunciation(
        word_id=word.id,
        phonetic="ig-ZAM-pul",
        ipa_american="/ɪɡˈzæmpəl/"
    )
    await pronunciation.save()
    
    definition = Definition(
        word_id=word.id,
        part_of_speech="noun",
        text="a representative form or pattern",
        meaning_cluster=MeaningCluster(
            id="example_pattern",
            name="Pattern sense",
            description="Something that serves as a pattern",
            order=0,
            relevance=0.8
        ),
        cefr_level="B1",
        frequency_band=2
    )
    await definition.save()
    
    fact = Fact(
        word_id=word.id,
        content="The word 'example' comes from Latin",
        category="etymology",
        model_info=ModelInfo(name="gpt-4", confidence=0.9, generation_count=1)
    )
    await fact.save()
    
    # Create synthesized entry
    synth_entry = SynthesizedDictionaryEntry(
        word_id=word.id,
        pronunciation_id=pronunciation.id,
        definition_ids=[definition.id],
        etymology=Etymology(
            text="From Latin exemplum",
            origin_language="Latin",
            root_words=["exemplum"]
        ),
        fact_ids=[fact.id],
        model_info=ModelInfo(
            name="gpt-4",
            confidence=0.95,
            generation_count=1
        ),
        source_provider_data_ids=[]
    )
    await synth_entry.save()
    
    # Verify complete structure
    assert synth_entry.word_id == word.id
    assert len(synth_entry.definition_ids) == 1
    assert synth_entry.etymology.origin_language == "Latin"
    assert synth_entry.model_info.confidence == 0.95


@pytest.mark.asyncio
async def test_definition_linguistic_fields(db):
    """Test Definition with comprehensive linguistic data."""
    word = Word(text="give", normalized="give", language=Language.ENGLISH)
    await word.save()
    
    definition = Definition(
        word_id=word.id,
        part_of_speech="verb",
        text="transfer possession of something",
        meaning_cluster=MeaningCluster(
            id="give_transfer",
            name="Transfer sense",
            description="Physical or abstract transfer",
            order=0,
            relevance=0.95
        ),
        sense_number="1a",
        register="neutral",
        domain=None,  # General use
        transitivity="transitive",
        cefr_level="A1",
        frequency_band=1,
        grammar_patterns=[
            {"pattern": "[Dn.n]", "description": "Ditransitive"}
        ],
        collocations=[
            {"text": "give away", "type": "verb", "frequency": 0.8}
        ],
        usage_notes=[
            {"type": "grammar", "text": "Irregular past: gave"}
        ]
    )
    await definition.save()
    
    assert definition.transitivity == "transitive"
    assert definition.cefr_level == "A1"
    assert len(definition.grammar_patterns) == 1
    assert definition.grammar_patterns[0]["pattern"] == "[Dn.n]"


@pytest.mark.asyncio
async def test_model_versioning(db):
    """Test version tracking on updates."""
    word = Word(text="version", normalized="version", language=Language.ENGLISH)
    await word.save()
    
    original_version = word.version
    original_updated = word.updated_at
    
    # Update word
    word.offensive_flag = True
    word.version += 1
    word.updated_at = datetime.utcnow()
    await word.save()
    
    assert word.version == original_version + 1
    assert word.updated_at > original_updated


@pytest.mark.asyncio 
async def test_fact_categories(db):
    """Test Fact with different categories."""
    word = Word(text="etymology", normalized="etymology", language=Language.ENGLISH)
    await word.save()
    
    categories = ["etymology", "usage", "cultural", "linguistic", "historical"]
    facts = []
    
    for category in categories:
        fact = Fact(
            word_id=word.id,
            content=f"Test fact about {category}",
            category=category,
            model_info=ModelInfo(name="gpt-4", confidence=0.8, generation_count=1)
        )
        await fact.save()
        facts.append(fact)
    
    # Retrieve all facts for word
    retrieved_facts = await Fact.find(Fact.word_id == word.id).to_list()
    assert len(retrieved_facts) == len(categories)
    
    retrieved_categories = {f.category for f in retrieved_facts}
    assert retrieved_categories == set(categories)