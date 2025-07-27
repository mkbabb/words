# Batch Synthesis Script

A robust batch processing script for synthesizing dictionary entries with OpenAI's Batch API, providing 50% cost reduction compared to regular API calls.

## Features

- **Rich Console Output**: Beautiful progress bars and real-time status updates
- **Cost Tracking**: Monitors token usage and estimates costs
- **Time Estimation**: Shows processing speed and ETA
- **Checkpoint/Resume**: Automatically saves progress and can resume from interruptions
- **Graceful Shutdown**: Handles Ctrl+C gracefully, finishing current batch
- **Error Recovery**: Tracks failed words and continues processing
- **Batch API Integration**: Uses OpenAI's Batch API for 50% cost savings

## Usage

```bash
# Basic usage
./batch_synthesis.py words.txt

# With custom checkpoint file
./batch_synthesis.py words.txt --checkpoint my_checkpoint.json

# Adjust batch size (default: 10)
./batch_synthesis.py words.txt --batch-size 20

# Dry run to see cost estimates
./batch_synthesis.py words.txt --dry-run
```

## Input Format

Create a text file with one word per line:

```
efflorescence
perspicacious
mellifluous
```

## Output

The script provides:

1. **Real-time Progress**: Shows current word being processed, progress bar, and time estimates
2. **Cost Tracking**: Displays total tokens used and estimated costs
3. **Status Table**: Updates with metrics like words/minute, success rate, and ETA
4. **Checkpoint File**: JSON file saving progress for resume capability

## Example Output

```
📚 Total words: 100
✅ Already processed: 25
📝 Remaining: 75

┌─────────────────────────────────┐
│        Cost Estimates           │
├─────────────────────────────────┤
│ Regular API Cost: $3.75         │
│ Batch API Cost: $1.88           │
│ Savings: $1.87 (50% off)        │
│ Estimated Tokens: 375,000       │
└─────────────────────────────────┘

🚀 Proceed with batch synthesis? [y/N]: y

Processing words... ━━━━━━━━━━━━━━━━━━━━ 75/75 100% 0:12:34

┌─────────────────────────────────┐
│    Batch Synthesis Status       │
├─────────────────┬───────────────┤
│ Metric          │ Value         │
├─────────────────┼───────────────┤
│ Total Words     │ 100           │
│ Processed       │ 100           │
│ Failed          │ 2             │
│ Success Rate    │ 98.0%         │
│ Words/Minute    │ 7.9           │
│ Total Tokens    │ 382,456       │
│ Total Cost      │ $1.91         │
│ Elapsed Time    │ 0:12:34       │
│ ETA             │ N/A           │
└─────────────────┴───────────────┘

✅ Batch synthesis complete!
```

## Checkpoint Format

The checkpoint file saves:

```json
{
  "processed_words": ["word1", "word2"],
  "failed_words": {
    "word3": "API error: rate limit"
  },
  "start_time": 1234567890.0,
  "total_cost": 1.91,
  "total_tokens": 382456,
  "timestamp": "2025-01-27T10:30:00"
}
```

## Error Handling

- **Graceful Shutdown**: Press Ctrl+C to stop processing after current batch
- **Automatic Retry**: Failed words are tracked but don't stop processing
- **Resume Support**: Run again with same checkpoint to continue where left off

## Cost Optimization

The script uses OpenAI's Batch API which provides:
- 50% discount on all API calls
- Higher rate limits
- 24-hour completion window
- Automatic queuing and processing

## Requirements

- Python 3.12+
- Backend dependencies installed (`uv sync`)
- OpenAI API key configured
- MongoDB running (for storage)