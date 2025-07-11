<template>
  <div class="legendre-series-approximation">
    <Card>
      <CardHeader>
        <CardTitle>Legendre Series Approximation</CardTitle>
      </CardHeader>
      <CardContent>
        <div class="controls">
          <div class="input-section">
            <label>Input Type:</label>
            <select v-model="inputType" class="input-select">
              <option value="function">Function Samples</option>
              <option value="image">Image Upload</option>
            </select>
          </div>

          <div v-if="inputType === 'function'" class="function-input">
            <label>Sample Function:</label>
            <select v-model="selectedFunction" class="input-select">
              <option value="sine">sin(πx)</option>
              <option value="gaussian">Gaussian</option>
              <option value="step">Step Function</option>
              <option value="custom">Custom</option>
            </select>
            
            <div v-if="selectedFunction === 'custom'" class="custom-input">
              <Input
                v-model="customExpression"
                placeholder="Enter expression (e.g., x^2 - 0.5)"
                class="mt-2"
              />
            </div>
          </div>

          <div v-else class="image-input">
            <input
              type="file"
              ref="fileInput"
              accept="image/*"
              @change="handleFileChange"
              class="file-input"
            />
            <label>Encoding Method:</label>
            <select v-model="encodingMethod" class="input-select">
              <option value="luminance">Luminance</option>
              <option value="hilbert">Hilbert Transform</option>
              <option value="rgb_complex">RGB Complex</option>
            </select>
          </div>

          <div class="harmonics-control">
            <label>Number of Harmonics: {{ nHarmonics }}</label>
            <input
              type="range"
              v-model.number="nHarmonics"
              min="1"
              max="50"
              class="slider"
            />
          </div>

          <Button @click="computeApproximation" :disabled="computing">
            {{ computing ? 'Computing...' : 'Compute Approximation' }}
          </Button>
        </div>

        <div v-if="result" class="results">
          <div class="visualization">
            <canvas ref="canvasRef" :width="canvasWidth" :height="canvasHeight"></canvas>
          </div>

          <div class="metrics">
            <div class="metric">
              <span class="label">MSE:</span>
              <span class="value">{{ result.mse.toExponential(2) }}</span>
            </div>
            <div class="metric">
              <span class="label">Harmonics Used:</span>
              <span class="value">{{ result.n_harmonics }}</span>
            </div>
          </div>

          <div v-if="imageResult" class="image-result">
            <h4>Reconstructed Image:</h4>
            <img :src="imageResult.reconstructed_image" alt="Reconstructed" />
            <div class="metric">
              <span class="label">Quality:</span>
              <span class="value">{{ (imageResult.approximation_quality * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { gsap } from 'gsap';
import { legendreApi, type LegendreSeriesResult } from '@/utils/api';
import Card from '@/components/ui/Card.vue';
import CardContent from '@/components/ui/CardContent.vue';
import CardHeader from '@/components/ui/CardHeader.vue';
import CardTitle from '@/components/ui/CardTitle.vue';
import Button from '@/components/ui/Button.vue';
import Input from '@/components/ui/Input.vue';

const inputType = ref<'function' | 'image'>('function');
const selectedFunction = ref('sine');
const customExpression = ref('');
const nHarmonics = ref(20);
const computing = ref(false);
const result = ref<LegendreSeriesResult | null>(null);
const imageResult = ref<any>(null);
const encodingMethod = ref('luminance');
const selectedFile = ref<File | null>(null);

const fileInput = ref<HTMLInputElement>();
const canvasRef = ref<HTMLCanvasElement>();
const canvasWidth = 600;
const canvasHeight = 300;

// Generate function samples
const generateSamples = (nPoints: number = 200): number[] => {
  const x = Array.from({ length: nPoints }, (_, i) => -1 + (2 * i) / (nPoints - 1));
  
  switch (selectedFunction.value) {
    case 'sine':
      return x.map(xi => Math.sin(Math.PI * xi));
    
    case 'gaussian':
      return x.map(xi => Math.exp(-5 * xi * xi));
    
    case 'step':
      return x.map(xi => xi < 0 ? -1 : 1);
    
    case 'custom':
      try {
        // Simple expression parser (for demo)
        return x.map(xi => {
          const expr = customExpression.value.replace(/x/g, xi.toString());
          return eval(expr);
        });
      } catch {
        return x.map(() => 0);
      }
    
    default:
      return x.map(() => 0);
  }
};

// Handle file selection
const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0];
  }
};

// Compute approximation
const computeApproximation = async () => {
  computing.value = true;
  imageResult.value = null;
  
  try {
    if (inputType.value === 'function') {
      const samples = generateSamples();
      result.value = await legendreApi.computeSeries(samples, nHarmonics.value);
      drawVisualization(samples);
    } else if (selectedFile.value) {
      const imgResult = await legendreApi.processImage(
        selectedFile.value,
        encodingMethod.value,
        nHarmonics.value,
        'magnitude'
      );
      imageResult.value = imgResult;
      result.value = {
        coefficients: imgResult.coefficients,
        approximated_values: [],
        n_harmonics: imgResult.n_harmonics,
        mse: 0
      };
    }
  } catch (error) {
    console.error('Error computing approximation:', error);
  } finally {
    computing.value = false;
  }
};

// Draw visualization
const drawVisualization = (originalSamples: number[]) => {
  if (!canvasRef.value || !result.value) return;
  
  const ctx = canvasRef.value.getContext('2d');
  if (!ctx) return;
  
  // Clear canvas
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);
  
  // Setup
  const margin = 40;
  const plotWidth = canvasWidth - 2 * margin;
  const plotHeight = canvasHeight - 2 * margin;
  
  // Draw axes
  ctx.strokeStyle = '#888';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(margin, margin + plotHeight / 2);
  ctx.lineTo(margin + plotWidth, margin + plotHeight / 2);
  ctx.moveTo(margin, margin);
  ctx.lineTo(margin, margin + plotHeight);
  ctx.stroke();
  
  // Scale functions
  const xScale = (x: number) => margin + (x + 1) * plotWidth / 2;
  const yScale = (y: number) => margin + plotHeight / 2 - y * plotHeight / 3;
  
  // Draw original function
  ctx.strokeStyle = '#3b82f6';
  ctx.lineWidth = 2;
  ctx.beginPath();
  const nPoints = originalSamples.length;
  for (let i = 0; i < nPoints; i++) {
    const x = -1 + 2 * i / (nPoints - 1);
    const y = originalSamples[i];
    if (i === 0) {
      ctx.moveTo(xScale(x), yScale(y));
    } else {
      ctx.lineTo(xScale(x), yScale(y));
    }
  }
  ctx.stroke();
  
  // Draw approximation
  if (result.value.approximated_values.length > 0) {
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    for (let i = 0; i < result.value.approximated_values.length; i++) {
      const x = -1 + 2 * i / (result.value.approximated_values.length - 1);
      const y = result.value.approximated_values[i];
      if (i === 0) {
        ctx.moveTo(xScale(x), yScale(y));
      } else {
        ctx.lineTo(xScale(x), yScale(y));
      }
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }
  
  // Legend
  ctx.font = '14px sans-serif';
  ctx.fillStyle = '#3b82f6';
  ctx.fillText('Original', margin + 10, margin - 10);
  ctx.fillStyle = '#ef4444';
  ctx.fillText('Approximation', margin + 80, margin - 10);
};

onMounted(() => {
  // Initial setup if needed
});
</script>

<style scoped>
canvas {
  image-rendering: crisp-edges;
  image-rendering: -moz-crisp-edges;
  image-rendering: -webkit-crisp-edges;
  image-rendering: pixelated;
}
</style>