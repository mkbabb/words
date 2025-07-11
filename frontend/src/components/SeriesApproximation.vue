<template>
  <div class="space-y-6">
    <!-- Input Configuration -->
    <div class="grid gap-6 md:grid-cols-2">
      <!-- Function Input -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base">Function Input</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <Label>Sample Function</Label>
            <DropdownMenu
              v-model="selectedFunction"
              :options="functionOptions"
              placeholder="Select a function..."
            />
          </div>
          
          <div v-if="selectedFunction === 'custom'" class="space-y-2">
            <Label>Custom Expression</Label>
            <Input
              v-model="customExpression"
              placeholder="e.g., x^2 - 0.5"
              class="font-mono text-sm"
            />
          </div>
          
          <Button
            @click="generateFunctionSamples"
            variant="outline"
            size="sm"
            class="w-full"
            :disabled="!selectedFunction"
          >
            <Play class="w-4 h-4 mr-2" />
            Generate Samples
          </Button>
        </CardContent>
      </Card>

      <!-- Image Input -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base">Image Input</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <Label>Upload Image</Label>
            <input
              type="file"
              ref="fileInputRef"
              accept="image/*"
              @change="handleFileChange"
              class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            />
          </div>
          
          <div class="space-y-2 mt-4">
            <Label>Encoding Method</Label>
            <DropdownMenu
              v-model="encodingMethod"
              :options="encodingOptions"
              placeholder="Select encoding..."
            />
          </div>
          
          <Button
            @click="processImage"
            variant="outline"
            size="sm"
            class="w-full"
            :disabled="!selectedFile"
          >
            <ImageIcon class="w-4 h-4 mr-2" />
            Process Image
          </Button>
        </CardContent>
      </Card>
    </div>

    <!-- Approximation Controls -->
    <Card>
      <CardHeader>
        <CardTitle class="flex items-center justify-between">
          <span>Approximation Settings</span>
          <Badge v-if="currentSamples.length > 0" variant="secondary">
            {{ currentSamples.length }} samples
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-4">
        <div class="grid gap-4 md:grid-cols-2">
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <Label>Number of Harmonics</Label>
              <span class="text-sm font-mono text-muted-foreground">
                {{ harmonics }}
              </span>
            </div>
            <Slider
              :modelValue="harmonics"
              @update:modelValue="updateHarmonics"
              :min="1"
              :max="50"
              :step="1"
              class="w-full"
            />
          </div>
          
          <div class="flex items-end">
            <Button
              @click="computeApproximation"
              :disabled="computing || currentSamples.length === 0"
              class="w-full"
            >
              <Loader2 v-if="computing" class="w-4 h-4 mr-2 animate-spin" />
              <Calculator v-else class="w-4 h-4 mr-2" />
              {{ computing ? 'Computing...' : 'Compute Approximation' }}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Results -->
    <Card v-if="result" class="border-l-4 border-l-primary">
      <CardHeader>
        <CardTitle class="flex items-center justify-between">
          <span>Approximation Results</span>
          <Badge variant="outline">
            Quality: {{ (100 - result.mse * 100).toFixed(1) }}%
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent class="space-y-6">
        <!-- Visualization -->
        <div class="rounded-lg border bg-gradient-to-br from-background to-muted/20 p-4">
          <canvas
            ref="canvasRef"
            :width="canvasWidth"
            :height="canvasHeight"
            class="w-full h-auto rounded border"
          />
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="rounded-lg border bg-muted/30 p-4 text-center">
            <div class="text-2xl font-bold text-primary">
              {{ result.mse.toExponential(2) }}
            </div>
            <div class="text-sm text-muted-foreground">Mean Squared Error</div>
          </div>
          
          <div class="rounded-lg border bg-muted/30 p-4 text-center">
            <div class="text-2xl font-bold text-primary">
              {{ result.n_harmonics }}
            </div>
            <div class="text-sm text-muted-foreground">Harmonics Used</div>
          </div>
          
          <div class="rounded-lg border bg-muted/30 p-4 text-center">
            <div class="text-2xl font-bold text-primary">
              {{ result.coefficients.length }}
            </div>
            <div class="text-sm text-muted-foreground">Coefficients</div>
          </div>
        </div>

        <!-- Image Results -->
        <div v-if="imageResult" class="space-y-4">
          <Separator />
          <div>
            <h4 class="text-lg font-semibold mb-3">Reconstructed Image</h4>
            <div class="grid gap-4 md:grid-cols-2">
              <div class="space-y-2">
                <Label class="text-sm">Original vs Reconstruction</Label>
                <div class="rounded-lg border overflow-hidden">
                  <img
                    :src="imageResult.reconstructed_image"
                    alt="Reconstructed"
                    class="w-full h-auto"
                  />
                </div>
              </div>
              <div class="space-y-4">
                <div class="rounded-lg border bg-muted/30 p-4">
                  <div class="text-lg font-bold text-primary">
                    {{ (imageResult.approximation_quality * 100).toFixed(1) }}%
                  </div>
                  <div class="text-sm text-muted-foreground">
                    Reconstruction Quality
                  </div>
                </div>
                <div class="text-sm text-muted-foreground">
                  <p>Original size: {{ imageResult.original_size[0] }} × {{ imageResult.original_size[1] }}</p>
                  <p>Encoding: {{ encodingMethod }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Calculator, Loader2, ImageIcon, Play } from 'lucide-vue-next'

import Card from '@/components/ui/Card.vue'
import CardContent from '@/components/ui/CardContent.vue'
import CardHeader from '@/components/ui/CardHeader.vue'
import CardTitle from '@/components/ui/CardTitle.vue'
import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'
import Slider from '@/components/ui/Slider.vue'
import Badge from '@/components/ui/Badge.vue'
import Separator from '@/components/ui/Separator.vue'
import DropdownMenu from '@/components/ui/DropdownMenu.vue'
import { legendreApi, type LegendreSeriesResult } from '@/utils/api'

interface Props {
  harmonics: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'harmonics-change': [value: number]
}>()

// Form data
const selectedFunction = ref('sine')
const customExpression = ref('')
const encodingMethod = ref('luminance')
const selectedFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement>()

// State
const computing = ref(false)
const currentSamples = ref<number[]>([])
const result = ref<LegendreSeriesResult | null>(null)
const imageResult = ref<any>(null)

// Canvas
const canvasRef = ref<HTMLCanvasElement>()
const canvasWidth = 600
const canvasHeight = 300

// Options
const functionOptions = [
  { value: 'sine', label: 'sin(πx)' },
  { value: 'gaussian', label: 'Gaussian' },
  { value: 'step', label: 'Step Function' },
  { value: 'polynomial', label: 'x² - 0.5' },
  { value: 'custom', label: 'Custom Expression' }
]

const encodingOptions = [
  { value: 'luminance', label: 'Luminance' },
  { value: 'hilbert', label: 'Hilbert Transform' },
  { value: 'rgb_complex', label: 'RGB Complex' }
]

// Methods
const updateHarmonics = (value: number) => {
  emit('harmonics-change', value)
}

const generateFunctionSamples = () => {
  const nPoints = 200
  const x = Array.from({ length: nPoints }, (_, i) => -1 + (2 * i) / (nPoints - 1))
  
  let samples: number[]
  
  switch (selectedFunction.value) {
    case 'sine':
      samples = x.map(xi => Math.sin(Math.PI * xi))
      break
    case 'gaussian':
      samples = x.map(xi => Math.exp(-5 * xi * xi))
      break
    case 'step':
      samples = x.map(xi => xi < 0 ? -1 : 1)
      break
    case 'polynomial':
      samples = x.map(xi => xi * xi - 0.5)
      break
    case 'custom':
      try {
        samples = x.map(xi => {
          const expr = customExpression.value.replace(/x/g, xi.toString())
          return eval(expr)
        })
      } catch {
        samples = x.map(() => 0)
      }
      break
    default:
      samples = x.map(() => 0)
  }
  
  currentSamples.value = samples
}

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files[0]) {
    selectedFile.value = target.files[0]
  }
}

const processImage = async () => {
  if (!selectedFile.value) return
  
  computing.value = true
  try {
    const imgResult = await legendreApi.processImage(
      selectedFile.value,
      encodingMethod.value,
      props.harmonics,
      'magnitude'
    )
    imageResult.value = imgResult
    currentSamples.value = imgResult.coefficients.map((c: any) => 
      typeof c === 'object' ? Math.sqrt(c.real * c.real + c.imag * c.imag) : c
    )
  } catch (error) {
    console.error('Error processing image:', error)
  } finally {
    computing.value = false
  }
}

const computeApproximation = async () => {
  if (currentSamples.value.length === 0) return
  
  computing.value = true
  try {
    const approximationResult = await legendreApi.computeSeries(
      currentSamples.value,
      props.harmonics
    )
    result.value = approximationResult
    drawVisualization()
  } catch (error) {
    console.error('Error computing approximation:', error)
  } finally {
    computing.value = false
  }
}

const drawVisualization = () => {
  if (!canvasRef.value || !result.value) return
  
  const ctx = canvasRef.value.getContext('2d')
  if (!ctx) return
  
  // Clear and setup
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)
  ctx.fillStyle = 'rgba(0, 0, 0, 0.02)'
  ctx.fillRect(0, 0, canvasWidth, canvasHeight)
  
  const margin = 40
  const plotWidth = canvasWidth - 2 * margin
  const plotHeight = canvasHeight - 2 * margin
  
  // Scales
  const xScale = (x: number) => margin + (x + 1) * plotWidth / 2
  const yScale = (y: number) => margin + plotHeight / 2 - y * plotHeight / 3
  
  // Draw grid
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)'
  ctx.lineWidth = 0.5
  for (let i = 0; i <= 10; i++) {
    const x = margin + (i * plotWidth) / 10
    ctx.beginPath()
    ctx.moveTo(x, margin)
    ctx.lineTo(x, margin + plotHeight)
    ctx.stroke()
  }
  
  // Draw original function
  ctx.strokeStyle = '#3b82f6'
  ctx.lineWidth = 3
  ctx.beginPath()
  currentSamples.value.forEach((sample, i) => {
    const x = -1 + 2 * i / (currentSamples.value.length - 1)
    const y = sample
    if (i === 0) {
      ctx.moveTo(xScale(x), yScale(y))
    } else {
      ctx.lineTo(xScale(x), yScale(y))
    }
  })
  ctx.stroke()
  
  // Draw approximation
  if (result.value.approximated_values.length > 0) {
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 2
    ctx.setLineDash([8, 4])
    ctx.beginPath()
    result.value.approximated_values.forEach((val, i) => {
      const x = -1 + 2 * i / (result.value!.approximated_values.length - 1)
      const y = typeof val === 'object' ? val.real || 0 : val
      if (i === 0) {
        ctx.moveTo(xScale(x), yScale(y))
      } else {
        ctx.lineTo(xScale(x), yScale(y))
      }
    })
    ctx.stroke()
    ctx.setLineDash([])
  }
  
  // Labels
  ctx.fillStyle = '#374151'
  ctx.font = '12px sans-serif'
  ctx.fillText('Original', margin + 10, margin - 10)
  ctx.fillStyle = '#ef4444'
  ctx.fillText('Approximation', margin + 80, margin - 10)
}
</script>

<style scoped>
canvas {
  image-rendering: crisp-edges;
}
</style>