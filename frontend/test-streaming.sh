#!/bin/bash

# Test script for streaming API progress tracking

echo "=== Testing Progress Tracking System ==="
echo ""

# Test 1: Single provider
echo "Test 1: Single Provider (wiktionary)"
echo "Expected progress points: 0% → 10% → 15% → 40% → 50% → 60% → 80% → 100%"
echo ""

curl -N -s "http://localhost:8000/api/lookup/hello/stream?providers=wiktionary" | while IFS= read -r line; do
    if [[ $line == event:* ]]; then
        event_type=${line#event: }
    elif [[ $line == data:* ]]; then
        data=${line#data: }
        if [[ $event_type == "progress" ]]; then
            # Extract progress value using grep and sed
            progress=$(echo "$data" | grep -o '"progress":[0-9.]*' | sed 's/"progress"://')
            stage=$(echo "$data" | grep -o '"stage":"[^"]*"' | sed 's/"stage":"\([^"]*\)"/\1/')
            message=$(echo "$data" | grep -o '"message":"[^"]*"' | sed 's/"message":"\([^"]*\)"/\1/')
            
            # Convert to percentage
            percent=$(echo "$progress * 100" | bc -l | xargs printf "%.0f")
            
            echo "  $stage: $progress ($percent%) - $message"
        elif [[ $event_type == "complete" ]]; then
            echo "  ✅ Complete event received"
            break
        elif [[ $event_type == "error" ]]; then
            echo "  ❌ Error: $data"
            break
        fi
    fi
done

echo ""
echo "Test 2: Multiple Providers (wiktionary, oxford, dictionary_com)"
echo "Expected provider progress to be divided: 15-23%, 23-31%, 31-40%"
echo ""

curl -N -s "http://localhost:8000/api/lookup/world/stream?providers=wiktionary&providers=oxford&providers=dictionary_com" | while IFS= read -r line; do
    if [[ $line == event:* ]]; then
        event_type=${line#event: }
    elif [[ $line == data:* ]]; then
        data=${line#data: }
        if [[ $event_type == "progress" ]]; then
            # Extract values
            progress=$(echo "$data" | grep -o '"progress":[0-9.]*' | sed 's/"progress"://')
            stage=$(echo "$data" | grep -o '"stage":"[^"]*"' | sed 's/"stage":"\([^"]*\)"/\1/')
            provider=$(echo "$data" | grep -o '"provider":"[^"]*"' | sed 's/"provider":"\([^"]*\)"/\1/' || echo "")
            
            # Convert to percentage
            percent=$(echo "$progress * 100" | bc -l | xargs printf "%.0f")
            
            if [[ -n $provider ]]; then
                echo "  $stage [$provider]: $progress ($percent%)"
            else
                echo "  $stage: $progress ($percent%)"
            fi
        elif [[ $event_type == "complete" ]]; then
            echo "  ✅ Complete"
            break
        fi
    fi
done

echo ""
echo "=== Progress Analysis ==="
echo ""
echo "Key checkpoints to verify:"
echo "1. Search starts at 0% and completes at 10%"
echo "2. Provider fetch starts at 15% and ends at 40%"
echo "3. For multiple providers, progress is divided proportionally"
echo "4. AI clustering at 40-50%"
echo "5. AI synthesis at 50-60%"
echo "6. Storage save at 80%"
echo "7. Complete at 100%"