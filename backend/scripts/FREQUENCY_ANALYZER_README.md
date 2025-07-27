# Frequency Analyzer

A comprehensive tool for analyzing word frequencies from multiple sources and generating prioritized word lists.

## Features

- **Multi-Source Frequency Data**: Downloads and processes frequency data from:
  - Google Trillion Word Corpus (10k most frequent)
  - COCA (Corpus of Contemporary American English)
  - Wikipedia frequency data
  - SUBTLEX-US (movie subtitle frequencies)
  - Common English word lists

- **Literary Corpus Processing**: Processes additional literary corpora for historical frequency analysis

- **Configurable Weights**: Apply custom weights to different sources based on importance

- **Multiple Output Sizes**: Generates word lists of various sizes (1k, 5k, 10k, 20k, 50k)

- **Lemmatization Support**: Groups inflected forms and tracks lemma relationships

- **Integration**: Seamlessly integrates with the existing corpus processing pipeline

## Usage

### Basic Usage

```bash
# Run frequency analysis with default settings
./scripts/frequency_analyzer.py

# Specify custom directories
./scripts/frequency_analyzer.py --data-dir custom/data --output-dir custom/output
```

### Custom Weights

Apply custom weights to frequency sources:

```bash
./scripts/frequency_analyzer.py --weights '{"google_10k": 3.0, "coca_5000": 4.0}'
```

### Integration with Corpus Processor

Filter frequency lists to only include base forms from corpus processing:

```bash
# First run corpus processor
./scripts/process_corpus.py

# Then run frequency analyzer with integration
./scripts/frequency_analyzer.py --integrate data/processed_corpus
```

### Adding Literary Corpora

Place literary text files in `data/corpora/` directory:

```bash
# Create corpora directory
mkdir -p data/corpora

# Add corpus files (txt or json)
cp shakespeare_complete.txt data/corpora/
cp modern_fiction.json data/corpora/

# Run analysis - corpora will be automatically processed
./scripts/frequency_analyzer.py
```

## Output Files

The analyzer generates several output files:

- `frequency_list_1000.txt` - Top 1,000 most frequent words
- `frequency_list_5000.txt` - Top 5,000 most frequent words
- `frequency_list_10000.txt` - Top 10,000 most frequent words
- `frequency_list_20000.txt` - Top 20,000 most frequent words
- `frequency_list_50000.txt` - Top 50,000 most frequent words
- `frequency_detailed.json` - Detailed frequency data with:
  - Combined frequencies for all words
  - Lemma mappings (base form → inflected forms)
  - Source information and weights used

## Source Weights

Default weights for frequency sources:

- **COCA (3.0)**: Highest weight - comprehensive, balanced corpus
- **SUBTLEX-US (2.5)**: High weight - reflects spoken/colloquial usage
- **Google 10k (2.0)**: High weight - web-based frequency
- **Wikipedia (1.8)**: Medium-high weight - encyclopedic content
- **Common words (1.5)**: Medium weight - general frequency lists
- **Literary corpora (0.5)**: Lower weight - historical/literary usage

## Integration with Floridify

The generated frequency lists can be used in the Floridify system for:

1. **Prioritized word lookups**: Process most common words first
2. **Vocabulary building**: Focus on high-frequency words for learners
3. **Anki deck generation**: Create frequency-based study decks
4. **Search optimization**: Boost common words in search results

## Advanced Features

### Lemma Tracking

The analyzer tracks relationships between base forms and inflected forms:

```json
{
  "lemma_mappings": {
    "run": ["runs", "running", "ran"],
    "good": ["better", "best"],
    "be": ["is", "are", "was", "were", "being", "been"]
  }
}
```

### Source Statistics

View detailed statistics about each source's contribution:

- Total words from each source
- Unique words not found in other sources
- Overlap between sources

### Filtered Lists

When integrated with corpus processing, creates filtered lists containing only base forms, reducing redundancy and focusing on root words.

## Examples

### Generate High-Priority Study List

```bash
# Generate top 5000 words with education-focused weights
./scripts/frequency_analyzer.py \
  --weights '{"coca_5000": 5.0, "subtlex_us": 2.0}' \
  --output-dir study_lists

# Use with Floridify batch processing
./scripts/batch_cli.py process study_lists/frequency_list_5000.txt
```

### Process Domain-Specific Corpus

```bash
# Add medical corpus
cp medical_terms.txt data/corpora/

# Run with custom weight for medical terms
./scripts/frequency_analyzer.py \
  --weights '{"corpus_medical_terms": 3.0}'
```

### Create Beginner Word List

```bash
# Generate and filter to basic words only
./scripts/frequency_analyzer.py --integrate data/processed_corpus

# The filtered/frequency_list_1000.txt will contain
# only base forms of the 1000 most common words
```