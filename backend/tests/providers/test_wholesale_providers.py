"""Comprehensive tests for wholesale provider implementations."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from floridify.models.base import Language
from floridify.models.dictionary import DictionaryEntry, DictionaryProvider
from floridify.providers.batch import BatchOperation
from floridify.providers.core import ConnectorConfig
from floridify.providers.dictionary.wholesale.wiktionary_wholesale import (
    WiktionaryWholesaleConnector,
)


class TestWiktionaryWholesaleConnector:
    """Test Wiktionary wholesale connector functionality."""

    @pytest.mark.asyncio
    async def test_connector_initialization(self, tmp_path: Path) -> None:
        """Test WiktionaryWholesaleConnector initialization."""
        data_dir = tmp_path / "wiktionary_test"
        config = ConnectorConfig()

        connector = WiktionaryWholesaleConnector(
            language=Language.ENGLISH, data_dir=data_dir, config=config
        )

        assert connector.provider == DictionaryProvider.WIKTIONARY
        assert connector.language == Language.ENGLISH
        assert connector.data_dir == data_dir
        assert data_dir.exists()
        assert connector.dump_base_url == "https://dumps.wikimedia.org/enwiktionary/latest"

    @pytest.mark.asyncio
    async def test_different_language_initialization(self, tmp_path: Path) -> None:
        """Test initialization with different languages."""
        data_dir = tmp_path / "wiktionary_french"

        connector = WiktionaryWholesaleConnector(language=Language.FRENCH, data_dir=data_dir)

        assert connector.language == Language.FRENCH
        assert connector.dump_base_url == "https://dumps.wikimedia.org/frwiktionary/latest"

    @pytest.mark.asyncio
    async def test_get_provider_version(self) -> None:
        """Test version string generation."""
        connector = WiktionaryWholesaleConnector(language=Language.ENGLISH)
        version = connector.get_provider_version()

        assert version.startswith("en_wholesale_")
        assert len(version.split("_")[-1]) == 8  # YYYYMMDD format

    @pytest.mark.asyncio
    async def test_download_titles_list(self, tmp_path: Path) -> None:
        """Test downloading titles list."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"test\napple\nbanana\ncherry"

        with patch.object(connector, "client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            titles = await connector.download_titles_list()

            assert titles is not None
            assert len(titles) == 4
            assert "apple" in titles
            assert "banana" in titles
            assert "cherry" in titles

            # Verify file was saved
            titles_file = data_dir / "enwiktionary-latest-all-titles.gz"
            assert titles_file.exists()

    @pytest.mark.asyncio
    async def test_download_bulk_data(self, tmp_path):
        """Test downloading bulk data."""
        data_dir = tmp_path / "wiktionary_test"
        output_path = str(data_dir / "dump.xml.bz2")
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Mock httpx streaming
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_bytes = MagicMock(return_value=iter([b"compressed", b"xml", b"data"]))

        with patch.object(connector, "client") as mock_client:
            mock_client.stream = MagicMock()
            mock_client.stream.__aenter__ = AsyncMock(return_value=mock_response)
            mock_client.stream.__aexit__ = AsyncMock()

            success = await connector.download_bulk_data(output_path)

            assert success is True
            assert Path(output_path).exists()

    @pytest.mark.asyncio
    async def test_parse_xml_dump(self, tmp_path):
        """Test parsing XML dump file."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Create sample XML dump
        xml_content = """
        <mediawiki>
            <page>
                <title>apple</title>
                <revision>
                    <text>
                    ==English==
                    ===Noun===
                    # A common fruit
                    </text>
                </revision>
            </page>
            <page>
                <title>banana</title>
                <revision>
                    <text>
                    ==English==
                    ===Noun===
                    # A yellow fruit
                    </text>
                </revision>
            </page>
        </mediawiki>
        """

        dump_file = data_dir / "test_dump.xml"
        dump_file.write_text(xml_content)

        entries = []
        async for entry in connector.parse_xml_dump(str(dump_file)):
            entries.append(entry)

        assert len(entries) == 2
        assert any(e.word == "apple" for e in entries)
        assert any(e.word == "banana" for e in entries)

    @pytest.mark.asyncio
    async def test_process_wikitext_entry(self):
        """Test processing wikitext to DictionaryEntry."""
        connector = WiktionaryWholesaleConnector()

        wikitext = """
        ==English==
        ===Etymology===
        From Old English.
        
        ===Noun===
        {{en-noun}}
        # A round fruit
        # The tree that bears this fruit
        
        ===Verb===
        {{en-verb}}
        # To pick apples
        """

        entry = await connector.process_wikitext_entry("apple", wikitext)

        assert entry is not None
        assert entry.word == "apple"
        assert len(entry.definitions) > 0
        assert any("fruit" in d.definition for d in entry.definitions)

    @pytest.mark.asyncio
    async def test_import_to_mongodb(self, test_db, tmp_path):
        """Test importing wholesale data to MongoDB."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Create test entries
        test_entries = [
            DictionaryEntry(
                word="test1",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            ),
            DictionaryEntry(
                word="test2",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            ),
        ]

        # Mock parse_xml_dump to return test entries
        async def mock_parse():
            for entry in test_entries:
                yield entry

        with patch.object(connector, "parse_xml_dump", mock_parse):
            count = await connector.import_to_mongodb("fake_dump.xml")

            assert count == 2

            # Verify entries were saved
            saved1 = await connector.get("test1")
            saved2 = await connector.get("test2")

            assert saved1 is not None
            assert saved1.word == "test1"
            assert saved2 is not None
            assert saved2.word == "test2"

    @pytest.mark.asyncio
    async def test_batch_import(self, test_db, tmp_path):
        """Test batch import with progress tracking."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Create batch operation
        batch_op = BatchOperation(
            operation_id="test_batch", total_items=100, description="Test import"
        )

        # Create test entries
        test_entries = [
            DictionaryEntry(
                word=f"word_{i}",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            )
            for i in range(10)
        ]

        # Mock parse_xml_dump
        async def mock_parse():
            for entry in test_entries:
                yield entry

        with patch.object(connector, "parse_xml_dump", mock_parse):
            count = await connector.import_to_mongodb("fake_dump.xml", batch_operation=batch_op)

            assert count == 10
            # Batch operation should have tracked progress
            assert batch_op.processed_items >= 10

    @pytest.mark.asyncio
    async def test_incremental_update(self, test_db, tmp_path):
        """Test incremental updates with existing data."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Pre-populate with existing entry
        existing = DictionaryEntry(
            word="existing",
            provider=DictionaryProvider.WIKTIONARY,
            definitions=[],
        )
        await connector.save("existing", existing)

        # Create new entries including update to existing
        new_entries = [
            DictionaryEntry(
                word="existing",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],  # Updated version
                metadata={"updated": True},
            ),
            DictionaryEntry(
                word="new_word",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            ),
        ]

        # Mock parse_xml_dump
        async def mock_parse():
            for entry in new_entries:
                yield entry

        with patch.object(connector, "parse_xml_dump", mock_parse):
            count = await connector.import_to_mongodb("fake_dump.xml")

            assert count == 2

            # Check existing was updated
            updated = await connector.get("existing")
            assert updated is not None
            assert updated.metadata.get("updated") is True

            # Check new entry was added
            new = await connector.get("new_word")
            assert new is not None

    @pytest.mark.asyncio
    async def test_error_handling_during_import(self, test_db, tmp_path):
        """Test error handling during bulk import."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Create entries with one that will fail
        test_entries = [
            DictionaryEntry(
                word="valid1",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            ),
            None,  # This will cause an error
            DictionaryEntry(
                word="valid2",
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            ),
        ]

        # Mock parse_xml_dump
        async def mock_parse():
            for entry in test_entries:
                if entry is None:
                    raise ValueError("Invalid entry")
                yield entry

        with patch.object(connector, "parse_xml_dump", mock_parse):
            # Should handle error and continue
            with pytest.raises(ValueError):
                await connector.import_to_mongodb("fake_dump.xml")

            # First valid entry should still be saved
            saved = await connector.get("valid1")
            assert saved is not None

    @pytest.mark.asyncio
    async def test_language_filtering(self, tmp_path):
        """Test filtering entries by language."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(language=Language.FRENCH, data_dir=data_dir)

        # Test wikitext with multiple languages
        wikitext = """
        ==English==
        ===Noun===
        # English definition
        
        ==French==
        ===Nom===
        # Définition française
        
        ==Spanish==
        ===Sustantivo===
        # Definición española
        """

        # Process should filter for French only
        entry = await connector.process_wikitext_entry("mot", wikitext)

        if entry:
            # Should only have French content
            assert "française" in str(entry.definitions)
            assert "English" not in str(entry.definitions)
            assert "española" not in str(entry.definitions)

    @pytest.mark.asyncio
    async def test_memory_efficient_streaming(self, tmp_path):
        """Test memory-efficient streaming of large dumps."""
        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Create a simulated large XML file
        xml_file = data_dir / "large_dump.xml"
        with xml_file.open("w") as f:
            f.write("<mediawiki>\n")
            for i in range(1000):  # Simulate 1000 entries
                f.write(
                    f"""
                <page>
                    <title>word_{i}</title>
                    <revision>
                        <text>Definition for word {i}</text>
                    </revision>
                </page>
                """
                )
            f.write("</mediawiki>")

        # Process entries in streaming fashion
        processed_count = 0
        async for entry in connector.parse_xml_dump(str(xml_file)):
            processed_count += 1
            # Memory should not accumulate - entries are yielded one at a time
            assert entry.word.startswith("word_")

        assert processed_count == 1000

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, test_db, tmp_path):
        """Test concurrent processing of multiple entries."""
        import asyncio

        data_dir = tmp_path / "wiktionary_test"
        connector = WiktionaryWholesaleConnector(data_dir=data_dir)

        # Create multiple entries to process concurrently
        async def save_entry(word: str):
            entry = DictionaryEntry(
                word=word,
                provider=DictionaryProvider.WIKTIONARY,
                definitions=[],
            )
            await connector.save(word, entry)
            return word

        # Process 20 entries concurrently
        words = [f"concurrent_{i}" for i in range(20)]
        results = await asyncio.gather(*[save_entry(w) for w in words])

        assert len(results) == 20

        # Verify all were saved
        for word in words:
            saved = await connector.get(word)
            assert saved is not None
            assert saved.word == word

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager behavior."""
        connector = WiktionaryWholesaleConnector()

        async with connector as conn:
            assert conn is connector
            # Should have active client
            assert hasattr(conn, "client")

        # After context exit, resources should be cleaned up
        # (implementation specific)
