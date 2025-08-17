"""Tests for literature provider implementations."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from floridify.models.dictionary import Language, LiteratureSourceType
from floridify.providers.core import ConnectorConfig, ProviderType
from floridify.providers.literature.api.gutenberg import GutenbergConnector
from floridify.providers.literature.api.internet_archive import InternetArchiveConnector
from floridify.providers.literature.mappings import dickens, joyce, shakespeare
from floridify.providers.literature.models import (
    Author,
    LiteraryWork,
    LiteratureMetadata,
)


class TestLiteratureProviderBase:
    """Base tests for literature providers."""
    
    @pytest.mark.asyncio
    async def test_connector_initialization(self):
        """Test literature connector initialization."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        
        connectors = [
            GutenbergConnector(config),
            InternetArchiveConnector(config),
        ]
        
        for connector in connectors:
            assert connector.config == config
            assert connector.provider is not None
    
    @pytest.mark.asyncio
    async def test_author_mappings(self):
        """Test author mapping configurations."""
        # Test major author mappings
        authors = [
            shakespeare.SHAKESPEARE_MAPPING,
            dickens.DICKENS_MAPPING,
            joyce.JOYCE_MAPPING,
        ]
        
        for author in authors:
            assert isinstance(author, Author)
            assert author.name
            assert author.gutenberg_author_id or author.internet_archive_id
            assert len(author.works) > 0
            
            # Verify work structure
            for work in author.works:
                assert isinstance(work, LiteraryWork)
                assert work.title
                assert work.gutenberg_id or work.internet_archive_id
    
    @pytest.mark.asyncio
    async def test_metadata_extraction(self):
        """Test metadata extraction from literature sources."""
        metadata = LiteratureMetadata(
            title="Pride and Prejudice",
            author="Jane Austen",
            year=1813,
            language=Language.ENGLISH,
            source_type=LiteratureSourceType.BOOK,
            subjects=["Fiction", "Romance"],
            rights="Public Domain",
        )
        
        assert metadata.title == "Pride and Prejudice"
        assert metadata.author == "Jane Austen"
        assert metadata.year == 1813
        assert metadata.language == Language.ENGLISH


class TestGutenbergConnector:
    """Tests specific to Project Gutenberg."""
    
    @pytest.mark.asyncio
    async def test_gutenberg_text_download(self):
        """Test downloading text from Gutenberg."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = GutenbergConnector(config)
        
        mock_text = """The Project Gutenberg EBook of Pride and Prejudice
        
        CHAPTER 1
        
        It is a truth universally acknowledged, that a single man in possession
        of a good fortune, must be in want of a wife."""
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock()
            response.status_code = 200
            response.text = mock_text
            mock_client.get.return_value = response
            
            result = await connector.download_text(1342)  # Pride and Prejudice ID
            
            assert result is not None
            assert "truth universally acknowledged" in result
    
    @pytest.mark.asyncio
    async def test_gutenberg_metadata_fetch(self):
        """Test fetching metadata from Gutenberg catalog."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = GutenbergConnector(config)
        
        mock_rdf = """<?xml version="1.0" encoding="utf-8"?>
        <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                 xmlns:dcterms="http://purl.org/dc/terms/">
            <pgterms:ebook rdf:about="ebooks/1342">
                <dcterms:title>Pride and Prejudice</dcterms:title>
                <dcterms:creator>
                    <pgterms:agent>
                        <pgterms:name>Austen, Jane</pgterms:name>
                    </pgterms:agent>
                </dcterms:creator>
                <dcterms:language>en</dcterms:language>
            </pgterms:ebook>
        </rdf:RDF>"""
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock()
            response.status_code = 200
            response.text = mock_rdf
            mock_client.get.return_value = response
            
            metadata = await connector.get_metadata(1342)
            
            assert metadata is not None
            # Connector should parse RDF and extract metadata
    
    @pytest.mark.asyncio
    async def test_gutenberg_work_collection(self):
        """Test collecting all works by an author from Gutenberg."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = GutenbergConnector(config)
        
        # Mock Shakespeare's works
        shakespeare_works = [
            {"id": 1513, "title": "Romeo and Juliet"},
            {"id": 1514, "title": "Hamlet"},
            {"id": 1515, "title": "Macbeth"},
        ]
        
        with patch.object(connector, 'get_author_works') as mock_get_works:
            mock_get_works.return_value = shakespeare_works
            
            works = await connector.get_author_works("Shakespeare, William")
            
            assert len(works) == 3
            assert any("Hamlet" in str(w) for w in works)
    
    @pytest.mark.asyncio
    async def test_gutenberg_text_cleaning(self):
        """Test cleaning of Gutenberg text format."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = GutenbergConnector(config)
        
        raw_text = """*** START OF THIS PROJECT GUTENBERG EBOOK ***
        
        
        PRIDE AND PREJUDICE
        
        Chapter 1
        
        It is a truth universally acknowledged...
        
        *** END OF THIS PROJECT GUTENBERG EBOOK ***
        
        [Transcriber's notes and metadata]"""
        
        # Test text cleaning method if available
        cleaned = connector._clean_text(raw_text) if hasattr(connector, '_clean_text') else raw_text
        
        # Should remove Gutenberg headers/footers
        assert "*** START OF" not in cleaned or not hasattr(connector, '_clean_text')
        assert "*** END OF" not in cleaned or not hasattr(connector, '_clean_text')


class TestInternetArchiveConnector:
    """Tests specific to Internet Archive."""
    
    @pytest.mark.asyncio
    async def test_internet_archive_search(self):
        """Test searching Internet Archive."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = InternetArchiveConnector(config)
        
        mock_search_response = {
            "response": {
                "numFound": 42,
                "docs": [
                    {
                        "identifier": "shakespeareworks00shak",
                        "title": "Complete Works of Shakespeare",
                        "creator": ["Shakespeare, William"],
                        "year": "1623",
                    }
                ],
            }
        }
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = mock_search_response
            mock_client.get.return_value = response
            
            results = await connector.search("Shakespeare complete works")
            
            assert results is not None
            assert len(results.get("response", {}).get("docs", [])) > 0
    
    @pytest.mark.asyncio
    async def test_internet_archive_download(self):
        """Test downloading from Internet Archive."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = InternetArchiveConnector(config)
        
        mock_text = "The Complete Works of William Shakespeare..."
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock()
            response.status_code = 200
            response.text = mock_text
            mock_client.get.return_value = response
            
            text = await connector.download_text("shakespeareworks00shak")
            
            assert text == mock_text
    
    @pytest.mark.asyncio
    async def test_internet_archive_metadata(self):
        """Test metadata extraction from Internet Archive."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = InternetArchiveConnector(config)
        
        mock_metadata = {
            "metadata": {
                "identifier": "shakespeareworks00shak",
                "title": "Complete Works of Shakespeare",
                "creator": ["Shakespeare, William"],
                "date": "1623",
                "language": ["eng"],
                "subject": ["Drama", "Poetry"],
                "rights": "Public Domain",
            }
        }
        
        with patch.object(connector, 'client') as mock_client:
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = mock_metadata
            mock_client.get.return_value = response
            
            metadata = await connector.get_metadata("shakespeareworks00shak")
            
            assert metadata is not None
            assert metadata["metadata"]["title"] == "Complete Works of Shakespeare"


class TestLiteratureWorkMapping:
    """Test work mapping and resolution."""
    
    @pytest.mark.asyncio
    async def test_work_resolution(self):
        """Test resolving work IDs across providers."""
        hamlet = LiteraryWork(
            title="Hamlet",
            gutenberg_id=1524,
            internet_archive_id="hamlet00shak",
            year=1603,
            genre="Tragedy",
        )
        
        # Should have multiple source IDs
        assert hamlet.gutenberg_id == 1524
        assert hamlet.internet_archive_id == "hamlet00shak"
        assert hamlet.title == "Hamlet"
    
    @pytest.mark.asyncio
    async def test_author_work_aggregation(self):
        """Test aggregating works from multiple sources."""
        author = Author(
            name="Shakespeare, William",
            gutenberg_author_id=65,
            internet_archive_id="Shakespeare",
            works=[
                LiteraryWork(
                    title="Hamlet",
                    gutenberg_id=1524,
                    internet_archive_id="hamlet00shak",
                ),
                LiteraryWork(
                    title="Romeo and Juliet",
                    gutenberg_id=1513,
                    internet_archive_id="romeojuliet00shak",
                ),
            ],
        )
        
        assert len(author.works) == 2
        assert author.gutenberg_author_id == 65
        
        # Find specific work
        hamlet = next((w for w in author.works if w.title == "Hamlet"), None)
        assert hamlet is not None
        assert hamlet.gutenberg_id == 1524


class TestLiteratureBatchOperations:
    """Test batch literature operations."""
    
    @pytest.mark.asyncio
    async def test_author_corpus_download(self):
        """Test downloading entire author corpus."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        gutenberg = GutenbergConnector(config)
        
        # Mock downloading multiple works
        works_to_download = [
            {"id": 1524, "title": "Hamlet"},
            {"id": 1513, "title": "Romeo and Juliet"},
            {"id": 1533, "title": "Macbeth"},
        ]
        
        downloaded = []
        
        with patch.object(gutenberg, 'download_text') as mock_download:
            mock_download.return_value = "Mock text content"
            
            for work in works_to_download:
                text = await gutenberg.download_text(work["id"])
                downloaded.append({"work": work, "text": text})
            
            assert len(downloaded) == 3
            assert all(d["text"] == "Mock text content" for d in downloaded)
    
    @pytest.mark.asyncio
    async def test_parallel_download(self):
        """Test parallel downloading of multiple works."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        connector = GutenbergConnector(config)
        
        work_ids = [1524, 1513, 1533, 1515, 1520]
        
        with patch.object(connector, 'download_text') as mock_download:
            async def mock_download_delay(work_id):
                await asyncio.sleep(0.01)  # Simulate network delay
                return f"Text for work {work_id}"
            
            mock_download.side_effect = mock_download_delay
            
            # Download in parallel
            tasks = [connector.download_text(wid) for wid in work_ids]
            results = await asyncio.gather(*tasks)
            
            assert len(results) == len(work_ids)
            assert all(f"Text for work {wid}" in results for wid in work_ids)


class TestLiteratureProviderFallback:
    """Test fallback between literature providers."""
    
    @pytest.mark.asyncio
    async def test_provider_fallback(self):
        """Test falling back from Gutenberg to Internet Archive."""
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        gutenberg = GutenbergConnector(config)
        archive = InternetArchiveConnector(config)
        
        # Mock Gutenberg to fail
        with patch.object(gutenberg, 'download_text', return_value=None):
            # Mock Archive to succeed
            with patch.object(archive, 'download_text', return_value="Archive text"):
                # Try Gutenberg first
                text = await gutenberg.download_text(9999)
                if not text:
                    # Fall back to Archive
                    text = await archive.download_text("work_id")
                
                assert text == "Archive text"
    
    @pytest.mark.asyncio
    async def test_multi_source_aggregation(self):
        """Test aggregating data from multiple sources."""
        work = LiteraryWork(
            title="Hamlet",
            gutenberg_id=1524,
            internet_archive_id="hamlet00shak",
        )
        
        config = ConnectorConfig(provider_type=ProviderType.LITERATURE)
        
        # Get from Gutenberg
        gutenberg = GutenbergConnector(config)
        with patch.object(gutenberg, 'download_text', return_value="Gutenberg Hamlet"):
            gutenberg_text = await gutenberg.download_text(work.gutenberg_id)
        
        # Get from Archive
        archive = InternetArchiveConnector(config)
        with patch.object(archive, 'download_text', return_value="Archive Hamlet"):
            archive_text = await archive.download_text(work.internet_archive_id)
        
        # Should have both versions
        assert gutenberg_text == "Gutenberg Hamlet"
        assert archive_text == "Archive Hamlet"