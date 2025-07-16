# Batch Processing Guide

## Overview

The Floridify batch processing system uses OpenAI's Batch API to cost-effectively synthesize dictionary entries for large word corpora. This system provides 50% cost savings compared to real-time API calls.

## Components

### 1. Word Normalization and Filtering
- **Simple Filter**: NLTK-based filtering with lemmatization
- **Word Reduction**: Plurals → singular, verb forms → infinitive
- **Stop Word Removal**: 421 English stop words excluded
- **Compression**: 60-80% word count reduction typical

### 2. Batch Processing Pipeline
- **OpenAI Batch API**: JSONL file uploads for background processing
- **Concurrent Jobs**: Up to 5 batch jobs simultaneously
- **Progress Monitoring**: Real-time status tracking
- **Error Handling**: Automatic retries and failure logging

### 3. Scheduler
- **Overnight Processing**: Automated runs during off-peak hours
- **Cost Controls**: Budget limits and usage tracking
- **State Persistence**: JSON-based state management
- **Incremental Processing**: Only unprocessed words

## Quick Start

### Installation Requirements

```bash
# Install Python dependencies
uv add nltk spacy openai rich

# Download NLTK data
python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"

# Download spaCy model (optional, for better normalization)
python -m spacy download en_core_web_sm
```

### Basic Usage

```bash
# Filter and preview words
uv run ./scripts/batch_cli.py filter-words --filter-preset moderate --limit 100

# Estimate costs
uv run ./scripts/batch_cli.py estimate-cost

# Run batch processing (manual)
uv run ./scripts/batch_cli.py process --words 1000 --batch-size 500

# Start scheduler (overnight processing)
uv run ./scripts/batch_cli.py scheduler start --frequency daily --run-time "02:00" --max-words 10000 --max-cost 50.0
```

## Deployment Options

### 1. Manual Execution

For one-time processing or testing:

```bash
# Process 5000 words with moderate filtering
uv run ./scripts/batch_cli.py process \\
    --words 5000 \\
    --batch-size 1000 \\
    --filter-preset moderate \\
    --output-dir ./batch_output_$(date +%Y%m%d)
```

### 2. Cron Scheduling (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add line for daily 2 AM processing
0 2 * * * cd /path/to/words && uv run ./scripts/batch_cli.py scheduler run-once --words 10000 >> /var/log/floridify_batch.log 2>&1
```

### 3. Systemd Service (Linux)

Create `/etc/systemd/system/floridify-batch.service`:

```ini
[Unit]
Description=Floridify Batch Processing Scheduler
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/words
Environment=PATH=/path/to/words/.venv/bin
ExecStart=/path/to/words/.venv/bin/uv run ./scripts/batch_cli.py scheduler start --frequency daily --run-time "02:00"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable floridify-batch
sudo systemctl start floridify-batch

# Check status
sudo systemctl status floridify-batch
```

### 4. Docker Deployment

Create `Dockerfile.batch`:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app
COPY . .

# Install dependencies
RUN uv sync

# Download NLTK data
RUN uv run python -c "import nltk; nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"

# Create entrypoint script
RUN echo '#!/bin/bash\\nexec uv run ./scripts/batch_cli.py scheduler start "$@"' > /entrypoint.sh \\
    && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

```bash
# Build and run
docker build -f Dockerfile.batch -t floridify-batch .
docker run -d \\
    --name floridify-scheduler \\
    -v $(pwd)/batch_output:/app/batch_output \\
    -v $(pwd)/cache:/app/cache \\
    -e OPENAI_API_KEY=your-key \\
    floridify-batch --frequency daily --run-time "02:00" --max-cost 50.0
```

## Configuration

### Environment Variables

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Optional MongoDB (defaults to localhost:27017)
export MONGODB_URL="mongodb://localhost:27017"
export MONGODB_DATABASE="floridify"

# Optional cache directory
export CACHE_DIR="./cache"
```

### Scheduler Configuration

```python
# In your Python code
from floridify.batch.scheduler import SchedulerConfig, ScheduleFrequency

config = SchedulerConfig(
    frequency=ScheduleFrequency.DAILY,
    run_time="02:00",  # 2 AM
    max_words_per_run=10000,
    max_cost_per_run=50.0,  # USD
    enable_auto_scaling=True,
    min_batch_size=500,
    max_batch_size=2000
)
```

## Cost Management

### OpenAI Usage Monitoring

OpenAI provides several tools for monitoring API usage and costs:

#### Usage API (December 2024)
The new Usage API provides granular usage data with filtering capabilities:

```python
import openai
from datetime import datetime, timedelta

client = openai.OpenAI()

# Get usage data with the new Usage API
def get_detailed_usage(days_back: int = 30):
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    # Convert to Unix timestamps
    start_timestamp = int(start_time.timestamp())
    end_timestamp = int(end_time.timestamp())
    
    # Usage API call (requires Admin API key)
    usage_data = client.usage.completions(
        start_time=start_timestamp,
        end_time=end_timestamp,
        bucket_width="1d",  # Options: '1m', '1h', '1d'
        group_by=["model", "project_id"]  # Optional grouping
    )
    
    return usage_data

# Cost tracking
def get_cost_data(days_back: int = 30):
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days_back)
    
    # Costs API endpoint
    cost_data = client.usage.costs(
        start_time=int(start_time.timestamp()),
        end_time=int(end_time.timestamp()),
        bucket_width="1d"
    )
    
    return cost_data

# Example usage
usage = get_detailed_usage(7)  # Last 7 days
costs = get_cost_data(7)

print(f"Total tokens used: {sum(d.n_generated_tokens_total for d in usage.data)}")
print(f"Total cost: ${sum(d.amount for d in costs.data):.2f}")
```

#### Usage Dashboard Features
- **Real-time monitoring**: Minute-level granularity available
- **Multi-project view**: Independent project selector
- **Model breakdown**: Usage by different OpenAI models
- **Filtering options**: By API key, project ID, user ID, model
- **Export capabilities**: CSV/JSON data export

#### Access Requirements
- Organization Owner role required for full dashboard access
- Admin API key needed for programmatic Usage API access
- Billing permissions required for cost data

### Cost Estimation

```bash
# Get cost estimates for different scenarios
uv run ./scripts/batch_cli.py estimate-cost

# Example output:
# Full corpus (269,309 words): $180.50
# Moderate filtering (40,396 words): $27.08  
# Aggressive filtering (26,931 words): $18.05
```

### Budget Controls

1. **Per-run limits**: Set `max_cost_per_run` in scheduler config
2. **Monthly budgets**: Configure in OpenAI dashboard
3. **Email alerts**: Set usage thresholds in OpenAI billing settings

## Monitoring and Troubleshooting

### Status Monitoring

```bash
# Check scheduler status
uv run ./scripts/batch_cli.py scheduler status

# Manual processing status
uv run ./scripts/batch_cli.py process --words 100 --batch-size 50
```

### Log Analysis

```bash
# View scheduler logs
tail -f batch_scheduler.log

# View batch processing output
ls -la batch_output/
cat batch_output/run_*/batch_*.jsonl
```

### Common Issues

1. **OpenAI API Rate Limits**: Batch API has different limits than real-time API
2. **Memory Usage**: Large word lists may require processing in chunks
3. **MongoDB Connection**: Ensure MongoDB is running and accessible
4. **Disk Space**: Batch files and results can be large

### Recovery Procedures

```bash
# Reset scheduler state (caution: loses progress tracking)
uv run python -c "
from floridify.batch.scheduler import BatchScheduler, SchedulerConfig
scheduler = BatchScheduler(SchedulerConfig(), None, None, None)
scheduler.reset_state()
"

# Reprocess failed words
uv run ./scripts/batch_cli.py process --words 1000 --force-refresh
```

## Performance Optimization

### Word Filtering Presets

- **Conservative**: 20% retention, best coverage
- **Moderate**: 15% retention, balanced approach  
- **Aggressive**: 10% retention, maximum cost savings

### Batch Size Tuning

- **Small batches (500-1000)**: Faster feedback, more overhead
- **Large batches (1500-2000)**: Better throughput, slower feedback
- **Auto-scaling**: Adjusts based on success rates

### Caching Strategy

The system uses multiple cache layers:
1. **Word normalization cache**: Persistent NLTK/spaCy results
2. **Definition cache**: HTTP responses from dictionary APIs
3. **Synthesis cache**: MongoDB storage for completed entries

## Advanced Usage

### Custom Word Lists

```python
# Process specific word list
from floridify.batch import BatchProcessor, BatchJobConfig

config = BatchJobConfig(
    batch_size=1000,
    providers=[WiktionaryConnector()],
    enable_clustering=True,
    enable_synthesis=True
)

processor = BatchProcessor(config, ai_connector, search_engine, mongodb)

# Custom word list
custom_words = ["serendipity", "ephemeral", "quintessential"]
result = await processor.run_batch_processing(word_limit=len(custom_words))
```

### Integration with Existing Systems

```python
# Add to existing workflow
async def daily_synthesis_job():
    scheduler = BatchScheduler(config, ai_connector, search_engine, mongodb)
    result = await scheduler.manual_run(word_limit=5000)
    
    # Send results to monitoring system
    send_metrics(result)
    
    return result
```

## Scheduler Execution Guide

### Understanding the Scheduler

The batch scheduler is designed for automated, overnight processing of large word corpora. It manages:

- **State persistence**: Tracks processing progress across runs
- **Cost controls**: Enforces budget limits and usage thresholds  
- **Job queuing**: Manages OpenAI Batch API jobs and monitoring
- **Incremental processing**: Only processes new/unprocessed words

### Execution Methods

#### 1. Interactive Mode (Development/Testing)
```bash
# Start scheduler interactively (blocks terminal)
uv run ./scripts/batch_cli.py scheduler start \\
    --frequency daily \\
    --run-time "02:00" \\
    --max-words 5000 \\
    --max-cost 25.0

# One-time run (immediate execution)
uv run ./scripts/batch_cli.py scheduler run-once --words 1000
```

#### 2. Background Daemon (Production)
```bash
# Start scheduler in background
nohup uv run ./scripts/batch_cli.py scheduler start \\
    --frequency daily \\
    --run-time "02:00" \\
    --max-words 10000 \\
    --max-cost 50.0 > scheduler.log 2>&1 &

# Check if running
ps aux | grep batch_cli
```

#### 3. Systemd Service (Recommended for Linux)
The systemd service provides automatic restart, logging, and system integration:

```bash
# Check service status
sudo systemctl status floridify-batch

# View logs
sudo journalctl -u floridify-batch -f

# Restart service
sudo systemctl restart floridify-batch

# Stop service
sudo systemctl stop floridify-batch
```

#### 4. Docker Container (Cloud/Containerized)
```bash
# Run scheduler container
docker run -d \\
    --name floridify-scheduler \\
    --restart unless-stopped \\
    -v $(pwd)/cache:/app/cache \\
    -v $(pwd)/batch_output:/app/batch_output \\
    -e OPENAI_API_KEY=sk-your-key \\
    -e MONGODB_URL=mongodb://host.docker.internal:27017 \\
    floridify-batch \\
    --frequency daily --run-time "02:00" --max-cost 50.0

# Monitor container logs
docker logs -f floridify-scheduler
```

### Scheduler Configuration Files

The scheduler creates and maintains several state files:

```
batch_scheduler_state.json     # Current processing state
batch_scheduler.log           # Execution logs  
cache/word_normalizer_*.json  # Normalization cache
batch_output/run_*/          # Processing results
```

### Monitoring Scheduler Health

#### Check Status Command
```bash
# Get current scheduler status
uv run ./scripts/batch_cli.py scheduler status

# Example output:
# Scheduler Status: WAITING
# Next run: 2025-01-08 02:00:00
# Words processed: 15,432 / 50,000
# Current cost: $23.45 / $50.00
# Active jobs: 2
```

#### Log Monitoring
```bash
# Real-time log monitoring
tail -f batch_scheduler.log

# Search for errors
grep -i error batch_scheduler.log

# Check completion rates
grep "Batch job completed" batch_scheduler.log | wc -l
```

### Troubleshooting Common Issues

#### Scheduler Won't Start
```bash
# Check Python/uv environment
uv run python --version
uv run python -c "import openai; print('OpenAI OK')"

# Verify API key
echo $OPENAI_API_KEY | cut -c1-10  # Should show 'sk-proj-...'

# Check MongoDB connection
uv run python -c "
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017')
print('MongoDB ping:', client.admin.command('ping'))
"
```

#### Scheduler Stops Unexpectedly  
```bash
# Check system resources
df -h    # Disk space
free -h  # Memory usage
top      # CPU usage

# Review error logs
tail -n 50 batch_scheduler.log | grep -i error

# Check for crashed processes
dmesg | grep -i "killed process"
```

#### Processing Appears Stuck
```bash
# Check OpenAI batch job status manually
uv run python -c "
import openai
client = openai.OpenAI()
jobs = client.batches.list(limit=10)
for job in jobs.data:
    print(f'{job.id}: {job.status} ({job.created_at})')
"

# Reset scheduler state (caution: loses progress)
uv run ./scripts/batch_cli.py scheduler reset-state
```

### Performance Tuning

#### Resource Requirements
- **RAM**: 2-4GB for moderate word lists (50K+ words)
- **Disk**: 1-5GB for batch files and caching
- **Network**: Stable connection for OpenAI API calls
- **CPU**: Minimal (mostly I/O bound operations)

#### Optimization Settings
```bash
# High-throughput processing
uv run ./scripts/batch_cli.py scheduler start \\
    --max-words 20000 \\
    --batch-size 2000 \\  # Larger batches = better throughput
    --filter-preset aggressive \\  # More aggressive filtering
    --max-cost 100.0

# Conservative processing (higher quality)
uv run ./scripts/batch_cli.py scheduler start \\
    --max-words 5000 \\
    --batch-size 500 \\   # Smaller batches = faster feedback
    --filter-preset conservative \\
    --max-cost 25.0
```

This system enables cost-effective, large-scale dictionary synthesis with comprehensive monitoring and control mechanisms.