#!/usr/bin/env node

/**
 * Comprehensive test script for progress tracking system
 * Tests backend streaming API and verifies progress values at every juncture
 */

import EventSource from 'eventsource';

const TEST_WORD = 'hello';
const API_BASE = 'http://localhost:8000/api';

// Expected progress checkpoints based on backend implementation
const EXPECTED_CHECKPOINTS = {
  'search_start': 0.0,
  'search_complete': 0.1,  // 10%
  'provider_fetch_start': 0.15, // 15%
  'provider_fetch_end': 0.40, // 40%
  'ai_clustering': 0.40, // 40%
  'ai_synthesis': 0.50, // 50-60%
  'storage_save': 0.80, // 80%
  'complete': 1.0 // 100%
};

// Progress tracking
const progressEvents = [];
let lastProgress = -1;

console.log('=== Testing Progress Tracking System ===\n');

// Test 1: Single provider
console.log('Test 1: Single Provider (wiktionary)');
testStreaming(['wiktionary'], () => {
  
  // Test 2: Multiple providers
  console.log('\nTest 2: Multiple Providers (wiktionary, oxford, dictionary_com)');
  testStreaming(['wiktionary', 'oxford', 'dictionary_com'], () => {
    
    // Test 3: Force refresh
    console.log('\nTest 3: Force Refresh with Multiple Providers');
    testStreamingWithRefresh(['wiktionary', 'oxford'], () => {
      console.log('\n=== All Tests Complete ===');
      analyzeResults();
    });
  });
});

function testStreaming(providers, callback) {
  progressEvents.length = 0;
  lastProgress = -1;
  
  const params = new URLSearchParams();
  providers.forEach(p => params.append('providers', p));
  
  const url = `${API_BASE}/lookup/${TEST_WORD}/stream?${params.toString()}`;
  console.log(`URL: ${url}`);
  
  const eventSource = new EventSource(url);
  
  eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    
    // Track progress event
    progressEvents.push({
      stage: data.stage,
      progress: data.progress,
      message: data.message,
      provider: data.details?.provider,
      timestamp: new Date().toISOString()
    });
    
    // Verify progress is increasing
    if (data.progress < lastProgress) {
      console.error(`❌ Progress went backwards! ${lastProgress} → ${data.progress}`);
    }
    lastProgress = data.progress;
    
    // Log progress update
    const percent = Math.round(data.progress * 100);
    const provider = data.details?.provider ? ` [${data.details.provider}]` : '';
    console.log(`  ${data.stage}${provider}: ${data.progress.toFixed(2)} (${percent}%) - ${data.message}`);
  });
  
  eventSource.addEventListener('complete', (event) => {
    console.log('  ✅ Complete event received');
    eventSource.close();
    setTimeout(callback, 500);
  });
  
  eventSource.addEventListener('error', (event) => {
    console.error('  ❌ Error:', event);
    eventSource.close();
    setTimeout(callback, 500);
  });
}

function testStreamingWithRefresh(providers, callback) {
  progressEvents.length = 0;
  lastProgress = -1;
  
  const params = new URLSearchParams();
  params.append('force_refresh', 'true');
  providers.forEach(p => params.append('providers', p));
  
  const url = `${API_BASE}/lookup/${TEST_WORD}/stream?${params.toString()}`;
  console.log(`URL: ${url}`);
  
  const eventSource = new EventSource(url);
  
  eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    
    // Track progress event
    progressEvents.push({
      stage: data.stage,
      progress: data.progress,
      message: data.message,
      provider: data.details?.provider,
      timestamp: new Date().toISOString()
    });
    
    // Verify progress is increasing
    if (data.progress < lastProgress) {
      console.error(`❌ Progress went backwards! ${lastProgress} → ${data.progress}`);
    }
    lastProgress = data.progress;
    
    // Log progress update
    const percent = Math.round(data.progress * 100);
    const provider = data.details?.provider ? ` [${data.details.provider}]` : '';
    console.log(`  ${data.stage}${provider}: ${data.progress.toFixed(2)} (${percent}%) - ${data.message}`);
  });
  
  eventSource.addEventListener('complete', (event) => {
    console.log('  ✅ Complete event received');
    eventSource.close();
    setTimeout(callback, 500);
  });
  
  eventSource.addEventListener('error', (event) => {
    console.error('  ❌ Error:', event);
    eventSource.close();
    setTimeout(callback, 500);
  });
}

function analyzeResults() {
  console.log('\n=== Progress Analysis ===');
  
  // Check for expected stages
  const stages = progressEvents.map(e => e.stage);
  const uniqueStages = [...new Set(stages)];
  console.log('\nUnique stages encountered:', uniqueStages);
  
  // Check progress values
  const progressValues = progressEvents.map(e => e.progress);
  console.log('\nProgress values:', progressValues.map(p => `${(p * 100).toFixed(0)}%`).join(' → '));
  
  // Verify monotonic increase
  let isMonotonic = true;
  for (let i = 1; i < progressValues.length; i++) {
    if (progressValues[i] < progressValues[i-1]) {
      isMonotonic = false;
      console.error(`\n❌ Non-monotonic progress at index ${i}: ${progressValues[i-1]} → ${progressValues[i]}`);
    }
  }
  
  if (isMonotonic) {
    console.log('\n✅ Progress values are monotonically increasing');
  }
  
  // Check critical checkpoints
  console.log('\n=== Critical Checkpoints ===');
  for (const [name, expectedValue] of Object.entries(EXPECTED_CHECKPOINTS)) {
    const found = progressEvents.find(e => Math.abs(e.progress - expectedValue) < 0.05);
    if (found) {
      console.log(`✅ ${name}: Expected ~${(expectedValue * 100).toFixed(0)}%, Found ${(found.progress * 100).toFixed(0)}%`);
    } else {
      console.log(`❌ ${name}: Expected ~${(expectedValue * 100).toFixed(0)}%, Not found`);
    }
  }
}