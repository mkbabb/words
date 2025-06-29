"""Comprehensive lexicon loader for English, French, and multilingual word support.

Loads word lists from various sources including:
1. NLTK word corpora (English, French)
2. Online word lists and dictionaries
3. Custom word files and user lists
4. Wiktionary entries and database words
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from .enums import LanguageCode, LexiconSource


class LexiconLoader:
    """Loads comprehensive word lexicons for multiple languages."""

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or Path("data/lexicons")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Word sources and their metadata
        self.word_sources = {
            LexiconSource.ENGLISH_COMMON.value: {
                "url": "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
                "size": "~370k words",
                "description": "Common English words",
            },
            LexiconSource.ENGLISH_COMPREHENSIVE.value: {
                "url": "https://raw.githubusercontent.com/dwyl/english-words/master/words.txt",
                "size": "~470k words",
                "description": "Comprehensive English dictionary",
            },
            LexiconSource.FRENCH_COMMON.value: {
                "url": "https://raw.githubusercontent.com/words/an-array-of-french-words/master/index.json",
                "size": "~336k words",
                "description": "French dictionary words (JSON format)",
                "format": "json",
            },
            LexiconSource.FRENCH_CONJUGATED.value: {
                "url": "https://raw.githubusercontent.com/Taknok/French-Wordlist/master/francais.txt",
                "size": "~60k words",
                "description": "French wordlist without diacritics",
            },
        }

        # Phrase and idiom sources
        self.phrase_sources = {
            "english_useful_phrases": {
                "url": "https://raw.githubusercontent.com/khvorostin/useful-english-phrases/master/01-useful-phrases.tsv",
                "size": "~15k phrases",
                "description": "Useful English phrases (TSV format)",
                "format": "tsv",
            },
            "english_significant_phrases": {
                "url": "https://raw.githubusercontent.com/khvorostin/useful-english-phrases/master/02-significant-phrases.txt",
                "size": "~5k phrases",
                "description": "Significant English phrases",
            },
            "english_felicitous_phrases": {
                "url": "https://raw.githubusercontent.com/khvorostin/useful-english-phrases/master/03-felicitous-phrases.txt",
                "size": "~5k phrases",
                "description": "Felicitous English phrases",
            },
            "english_impressive_phrases": {
                "url": "https://raw.githubusercontent.com/khvorostin/useful-english-phrases/master/04-impressive-phrases.txt",
                "size": "~5k phrases",
                "description": "Impressive English phrases",
            },
        }

        # Additional French phrases will be added to local collections

        # Local word collections (these will be loaded on demand)
        self.local_collections = {
            "english_academia": LexiconSource.ACADEMIC.value,
            "french_phrases": LexiconSource.FRENCH_PHRASES.value,
            "scientific_terms": LexiconSource.SCIENTIFIC.value,
            "proper_nouns": LexiconSource.PROPER_NOUNS.value,
        }

    async def load_all_lexicons(self, force_refresh: bool = False) -> dict[str, list[str]]:
        """Load all available word lexicons and phrase collections."""
        print("Loading comprehensive word lexicons and phrase collections...")

        all_words: dict[str, list[str]] = {}

        # Load online word sources
        for source_name, source_info in self.word_sources.items():
            print(f"Loading {source_name}: {source_info['description']}")

            # Use appropriate extension based on format
            file_format = source_info.get("format", "txt")
            cache_file = self.cache_dir / f"{source_name}.{file_format}"

            if cache_file.exists() and not force_refresh:
                # Load from cache
                words = await self._load_cached_words(cache_file, file_format)
            else:
                # Download and cache
                words = await self._download_word_list(source_info["url"], cache_file, file_format)

            all_words[source_name] = words
            print(f"  ✓ Loaded {len(words):,} words")

        # Load phrase sources
        for source_name, source_info in self.phrase_sources.items():
            print(f"Loading {source_name}: {source_info['description']}")

            # Use appropriate extension based on format
            file_format = source_info.get("format", "txt")
            cache_file = self.cache_dir / f"{source_name}.{file_format}"

            if cache_file.exists() and not force_refresh:
                # Load from cache
                phrases = await self._load_cached_words(cache_file, file_format)
            else:
                # Download and cache
                phrases = await self._download_word_list(
                    source_info["url"], cache_file, file_format
                )

            all_words[source_name] = phrases
            print(f"  ✓ Loaded {len(phrases):,} phrases")

        # Load local collections
        for collection_name, collection_type in self.local_collections.items():
            print(f"Loading {collection_name}")
            words = self._load_local_collection(collection_type)
            all_words[collection_name] = words
            print(f"  ✓ Generated {len(words):,} words/phrases")

        # Load from database if available
        try:
            db_words = await self._load_database_words()
            if db_words:
                all_words["database_words"] = db_words
                print(f"  ✓ Loaded {len(db_words):,} words from database")
        except Exception as e:
            print(f"  ⚠ Could not load database words: {e}")

        print(f"\nTotal lexicons loaded: {len(all_words)}")
        total_entries = sum(len(words) for words in all_words.values())
        print(f"Total word/phrase entries: {total_entries:,}")

        return all_words

    async def get_unified_lexicon(self, languages: list[LanguageCode] | None = None) -> list[str]:
        """Get a unified, deduplicated word list for specified languages."""
        if languages is None:
            languages = [LanguageCode.ENGLISH, LanguageCode.FRENCH]

        all_lexicons = await self.load_all_lexicons()

        # Collect words for specified languages
        unified_words: set[str] = set()

        for lang in languages:
            for source_name, words in all_lexicons.items():
                if lang.value in source_name.lower():
                    unified_words.update(word.lower().strip() for word in words)

        # Add database words and general collections
        for source_name, words in all_lexicons.items():
            if any(
                term in source_name
                for term in [
                    LexiconSource.DATABASE.value,
                    LexiconSource.SCIENTIFIC.value,
                    LexiconSource.PROPER_NOUNS.value,
                ]
            ):
                unified_words.update(word.lower().strip() for word in words)

        # Filter and clean (allow spaces for phrases)
        clean_words = []
        for word in unified_words:
            # Allow letters, spaces, hyphens, and apostrophes for phrases
            if (
                word
                and len(word) > 1
                and word.replace(" ", "").replace("-", "").replace("'", "").isalpha()
            ):
                clean_words.append(word)

        # Sort for consistency
        clean_words.sort()

        print(f"Unified lexicon created: {len(clean_words):,} unique words")
        return clean_words

    async def _download_word_list(
        self, url: str, cache_file: Path, file_format: str = "txt"
    ) -> list[str]:
        """Download word list from URL and cache locally."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                content = response.text
                words = self._parse_content(content, file_format)

                # Cache to file (always save as text for consistent caching)
                async with aiofiles.open(cache_file, "w", encoding="utf-8") as f:
                    await f.write("\n".join(words))

                return words

        except Exception as e:
            print(f"  ⚠ Failed to download {url}: {e}")
            return []

    async def _load_cached_words(self, cache_file: Path, file_format: str = "txt") -> list[str]:
        """Load words from cached file."""
        try:
            async with aiofiles.open(cache_file, encoding="utf-8") as f:
                content = await f.read()
                # All cached files are stored as plain text regardless of original format
                return [line.strip() for line in content.split("\n") if line.strip()]
        except Exception as e:
            print(f"  ⚠ Failed to load cache {cache_file}: {e}")
            return []

    def _parse_content(self, content: str, file_format: str) -> list[str]:
        """Parse content based on file format."""
        if file_format == "json":
            try:
                # Handle JSON arrays (like French words)
                data = json.loads(content)
                if isinstance(data, list):
                    return [str(word).strip() for word in data if word]
                else:
                    return []
            except json.JSONDecodeError:
                print("  ⚠ Failed to parse JSON content")
                return []

        elif file_format == "tsv":
            # Handle TSV format (Tab-Separated Values)
            lines = content.split("\n")
            words = []
            for line in lines:
                if line.strip():
                    # Split by tab and take the first column (the phrase)
                    parts = line.split("\t")
                    if parts and parts[0].strip():
                        words.append(parts[0].strip())
            return words

        else:
            # Default text format
            return [line.strip() for line in content.split("\n") if line.strip()]

    async def _load_database_words(self) -> list[str]:
        """Load words from the MongoDB database."""
        try:
            # This would integrate with the actual database
            # For now, return empty list as placeholder
            return []
        except Exception:
            return []

    def _load_local_collection(self, collection_type: str) -> list[str]:
        """Load a local word collection by type."""
        if collection_type == LexiconSource.ACADEMIC.value:
            return self._load_academic_english_words()
        elif collection_type == LexiconSource.FRENCH_PHRASES.value:
            return self._load_french_phrases()
        elif collection_type == LexiconSource.SCIENTIFIC.value:
            return self._load_scientific_terms()
        elif collection_type == LexiconSource.PROPER_NOUNS.value:
            return self._load_proper_nouns()
        else:
            return []

    def _load_academic_english_words(self) -> list[str]:
        """Load academic and scientific English vocabulary."""
        # Academic word list from various sources
        academic_words = [
            # Academic Word List (AWL) sublist 1
            "analysis",
            "approach",
            "area",
            "assessment",
            "assume",
            "authority",
            "available",
            "benefit",
            "concept",
            "consistent",
            "constitutional",
            "context",
            "contract",
            "create",
            "data",
            "definition",
            "derived",
            "distribution",
            "economic",
            "environment",
            "established",
            "estimate",
            "evidence",
            "export",
            "factors",
            "financial",
            "formula",
            "function",
            "identified",
            "income",
            "indicate",
            "individual",
            "interpretation",
            "involved",
            "issues",
            "labour",
            "legal",
            "legislation",
            "major",
            "method",
            "occur",
            "percent",
            "period",
            "policy",
            "principle",
            "procedure",
            "process",
            "required",
            "research",
            "response",
            "role",
            "section",
            "sector",
            "significant",
            "similar",
            "source",
            "specific",
            "structure",
            "theory",
            "variables",
            # Scientific terminology
            "hypothesis",
            "experiment",
            "methodology",
            "empirical",
            "theoretical",
            "statistical",
            "correlation",
            "causation",
            "phenomenon",
            "paradigm",
            "synthesis",
            "analysis",
            "algorithm",
            "heuristic",
            "optimization",
            "calibration",
            "validation",
            "verification",
            "quantitative",
            "qualitative",
            "longitudinal",
            "cross-sectional",
            "interdisciplinary",
            # French loanwords in English
            "entrepreneur",
            "renaissance",
            "cuisine",
            "genre",
            "boutique",
            "connoisseur",
            "rapport",
            "repertoire",
            "surveillance",
            "liaison",
            "avant-garde",
            "blasé",
            "bourgeois",
            "cliché",
            "déjà vu",
            "elite",
            "façade",
            "fiancé",
            "naïve",
            "protégé",
            "résumé",
            "soirée",
        ]

        return academic_words

    def _load_french_phrases(self) -> list[str]:
        """Load common French words and phrases used in English."""
        french_terms = [
            # Common French words
            "bonjour",
            "au revoir",
            "merci",
            "excusez-moi",
            "pardon",
            "oui",
            "non",
            "peut-être",
            "beaucoup",
            "très",
            "bien",
            "mal",
            "grand",
            "petit",
            "nouveau",
            "vieux",
            "jeune",
            "beau",
            "belle",
            "bon",
            "mauvais",
            # French phrases in English
            "c'est la vie",
            "joie de vivre",
            "raison d'être",
            "savoir-faire",
            "laissez-faire",
            "carte blanche",
            "coup de grâce",
            "double entendre",
            "fait accompli",
            "faux pas",
            "tour de force",
            "piece de resistance",
            # French culinary terms
            "hors d'oeuvres",
            "amuse-bouche",
            "entrée",
            "plat principal",
            "dessert",
            "apéritif",
            "digestif",
            "bon appétit",
            "chef",
            "sous chef",
            "maitre d'",
            "sommelier",
            "pâtissier",
            "boulanger",
            "croissant",
            "baguette",
            "brioche",
            "macaron",
            "éclair",
            "crème brûlée",
            # Fashion and arts
            "haute couture",
            "prêt-à-porter",
            "atelier",
            "couturier",
            "chic",
            "avant-garde",
            "art nouveau",
            "trompe l'oeil",
            "en plein air",
            # Academic and intellectual
            "critique",
            "oeuvre",
            "auteur",
            "élan vital",
            "zeitgeist",
            "weltanschauung",
            "gestalt",
            "schadenfreude",
            "sturm und drang",
        ]

        return french_terms

    def _load_scientific_terms(self) -> list[str]:
        """Load scientific and technical terminology."""
        scientific_terms = [
            # Biology
            "photosynthesis",
            "mitochondria",
            "chromosome",
            "DNA",
            "RNA",
            "protein",
            "enzyme",
            "metabolism",
            "homeostasis",
            "evolution",
            "biodiversity",
            "ecosystem",
            "phenotype",
            "genotype",
            "taxonomy",
            "phylogeny",
            # Chemistry
            "molecule",
            "atom",
            "electron",
            "proton",
            "neutron",
            "isotope",
            "catalyst",
            "reaction",
            "synthesis",
            "oxidation",
            "reduction",
            "electronegativity",
            "covalent",
            "ionic",
            "polar",
            "hydrophobic",
            # Physics
            "quantum",
            "relativity",
            "thermodynamics",
            "entropy",
            "wavelength",
            "frequency",
            "amplitude",
            "electromagnetic",
            "radiation",
            "particle",
            "acceleration",
            "velocity",
            "momentum",
            "energy",
            "force",
            # Mathematics
            "algorithm",
            "polynomial",
            "derivative",
            "integral",
            "matrix",
            "vector",
            "scalar",
            "eigenvalue",
            "topology",
            "asymptote",
            "convergence",
            "divergence",
            "infinity",
            "probability",
            "statistics",
            # Computer Science
            "algorithm",
            "heuristic",
            "optimization",
            "recursion",
            "iteration",
            "polymorphism",
            "encapsulation",
            "inheritance",
            "abstraction",
            "complexity",
            "scalability",
            "concurrency",
            "parallelism",
            "distributed",
            # Medicine
            "diagnosis",
            "prognosis",
            "symptom",
            "syndrome",
            "pathology",
            "etiology",
            "epidemiology",
            "pharmacology",
            "physiology",
            "anatomy",
            "immunology",
            "neurology",
            "cardiology",
            "oncology",
            "radiology",
        ]

        return scientific_terms

    def _load_proper_nouns(self) -> list[str]:
        """Load proper nouns and named entities."""
        proper_nouns = [
            # Countries and regions
            "afghanistan",
            "albania",
            "algeria",
            "andorra",
            "angola",
            "argentina",
            "armenia",
            "australia",
            "austria",
            "azerbaijan",
            "bahamas",
            "bahrain",
            "bangladesh",
            "barbados",
            "belarus",
            "belgium",
            "belize",
            "benin",
            "bhutan",
            "bolivia",
            "bosnia",
            "botswana",
            "brazil",
            "brunei",
            "bulgaria",
            "burkina",
            "burundi",
            "cambodia",
            "cameroon",
            "canada",
            # Major cities
            "london",
            "paris",
            "berlin",
            "madrid",
            "rome",
            "amsterdam",
            "vienna",
            "stockholm",
            "copenhagen",
            "helsinki",
            "oslo",
            "dublin",
            "edinburgh",
            "prague",
            "budapest",
            "warsaw",
            "moscow",
            "istanbul",
            "athens",
            "lisbon",
            "barcelona",
            "milan",
            "naples",
            "florence",
            "venice",
            # Common names (for completeness)
            "alexander",
            "alexandra",
            "andrew",
            "anna",
            "anthony",
            "barbara",
            "catherine",
            "charles",
            "christopher",
            "david",
            "elizabeth",
            "emily",
            "daniel",
            "emma",
            "ethan",
            "grace",
            "hannah",
            "isabella",
            "jacob",
            "james",
            "jennifer",
            "john",
            "joseph",
            "joshua",
            "julia",
            "kevin",
            "laura",
            "maria",
            "mark",
            "matthew",
            "michael",
            "michelle",
            "nicole",
            "olivia",
            "patricia",
            "paul",
            "richard",
            "robert",
            "samantha",
            "sarah",
            "stephanie",
            "thomas",
            "william",
            "benjamin",
            "natalie",
        ]

        return proper_nouns

    def get_lexicon_stats(self) -> dict[str, Any]:
        """Get statistics about available lexicons."""
        return {
            "online_sources": len(self.word_sources),
            "local_collections": len(self.local_collections),
            "total_sources": len(self.word_sources) + len(self.local_collections),
            "cache_dir": str(self.cache_dir),
            "sources_info": self.word_sources,
        }
