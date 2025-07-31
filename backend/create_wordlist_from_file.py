#!/usr/bin/env python3
"""Script to create a wordlist from words.txt file using REST API."""

import json
import re
import subprocess
from pathlib import Path


def main():
    """Parse words.txt and create wordlist via REST API."""
    words_file = Path("data/words.txt")
    
    if not words_file.exists():
        print(f"File {words_file} not found")
        return
    
    # Parse words from file
    words = []
    with open(words_file, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Extract word from numbered format: "1. Word" or "1. Word\t"
            match = re.match(r'^\d+\.\s*([^\t\s]+)', line)
            if match:
                word = match.group(1).strip()
                if word and word.isalpha():  # Only include alphabetic words
                    words.append(word.lower())  # Normalize to lowercase
    
    print(f"Parsed {len(words)} words from {words_file}")
    
    if not words:
        print("No words found")
        return
    
    # Remove duplicates while preserving order
    unique_words = list(dict.fromkeys(words))
    print(f"Found {len(unique_words)} unique words")
    
    # Create payload for API
    payload = {
        "name": "Advanced Vocabulary",
        "description": "Curated list of advanced English vocabulary words for language learning",
        "words": unique_words,
        "tags": ["vocabulary", "advanced", "english"],
        "is_public": False,
        "owner_id": "user_001"
    }
    
    # Call API using curl
    try:
        result = subprocess.run([
            'curl', '-X', 'POST',
            'http://localhost:8000/api/v1/wordlists',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if 'data' in response:
                    wordlist = response['data']
                    print(f"✅ Created wordlist: {wordlist['name']}")
                    print(f"   ID: {wordlist['id']}")
                    print(f"   Total words: {wordlist['total_words']}")
                    print(f"   Unique words: {wordlist['unique_words']}")
                    
                    # Display first 10 words as sample
                    if 'words' in wordlist and wordlist['words']:
                        print("\nFirst 10 words:")
                        for i, word_item in enumerate(wordlist['words'][:10]):
                            print(f"   {i+1}. {word_item['text']}")
                else:
                    print(f"✅ API Response: {response}")
            except json.JSONDecodeError:
                print(f"✅ Raw response: {result.stdout}")
        else:
            print(f"❌ API call failed: {result.stderr}")
            print(f"   Status code: {result.returncode}")
            print(f"   Response: {result.stdout}")
        
    except subprocess.TimeoutExpired:
        print("❌ API call timed out - make sure the backend server is running")
    except Exception as e:
        print(f"❌ Failed to call API: {e}")


if __name__ == "__main__":
    main()