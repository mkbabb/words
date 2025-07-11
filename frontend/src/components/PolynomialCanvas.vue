<template>
  <div class="relative">
    <svg
      ref="svgRef"
      :width="width"
      :height="height"
      class="w-full h-auto border rounded-lg bg-gradient-to-br from-background to-muted/20"
      :viewBox="`0 0 ${width} ${height}`"
      @mouseleave="hoveredPolynomial = null"
    >
      <defs>
        <!-- Grid pattern -->
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" stroke-width="0.5" stroke-dasharray="2,2" class="text-muted-foreground/20"/>
        </pattern>
        
        <!-- Gradient for axes -->
        <linearGradient id="axisGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.1"/>
          <stop offset="50%" stop-color="currentColor" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="currentColor" stop-opacity="0.1"/>
        </linearGradient>
        
        <!-- Clipping paths for polynomial animation -->
        <clipPath
          v-for="polynomial in visiblePolynomials"
          :key="`clip-${polynomial.degree}`"
          :id="`polynomial-clip-${polynomial.degree}`"
        >
          <rect
            x="80"
            y="0"
            :width="polynomial.clipWidth"
            :height="height"
          />
        </clipPath>
      </defs>

      <!-- Grid background -->
      <rect width="100%" height="100%" fill="url(#grid)" stroke-dasharray="2,2" />
      
      <!-- Coordinate system -->
      <g class="text-foreground">
        <!-- Main axes -->
        <defs>
          <marker id="arrowX" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
            <polygon points="0,0 0,6 9,3" fill="currentColor" />
          </marker>
          <marker id="arrowY" markerWidth="8" markerHeight="8" refX="4" refY="7" orient="270" markerUnits="strokeWidth">
            <polygon points="0,0 0,6 8,3" fill="currentColor" />
          </marker>
        </defs>
        
        <!-- Y-axis (arrow points down) -->
        <line 
          :x1="width/2" :y1="height-40" 
          :x2="width/2" :y2="40" 
          stroke="currentColor" 
          stroke-width="3" 
          marker-end="url(#arrowY)"
        />
        <!-- X-axis -->
        <line 
          :x1="80" :y1="height/2" 
          :x2="width-80" :y2="height/2" 
          stroke="currentColor" 
          stroke-width="3" 
          marker-end="url(#arrowX)"
        />
        
        <!-- Tick marks -->
        <g stroke="currentColor" stroke-width="2">
          <!-- X-axis ticks -->
          <line :x1="80" :y1="height/2 - 8" :x2="80" :y2="height/2 + 8" />
          <line :x1="width-80" :y1="height/2 - 8" :x2="width-80" :y2="height/2 + 8" />
          <line :x1="width*0.25 + 40" :y1="height/2 - 5" :x2="width*0.25 + 40" :y2="height/2 + 5" />
          <line :x1="width*0.75 - 40" :y1="height/2 - 5" :x2="width*0.75 - 40" :y2="height/2 + 5" />
          
          <!-- Y-axis ticks -->
          <line :x1="width/2 - 8" :y1="60" :x2="width/2 + 8" :y2="60" />
          <line :x1="width/2 - 8" :y1="height-60" :x2="width/2 + 8" :y2="height-60" />
          <line :x1="width/2 - 5" :y1="height*0.25 + 30" :x2="width/2 + 5" :y2="height*0.25 + 30" />
          <line :x1="width/2 - 5" :y1="height*0.75 - 30" :x2="width/2 + 5" :y2="height*0.75 - 30" />
        </g>
        
        <!-- Axis labels -->
        <g class="text-sm font-medium fill-foreground">
          <text :x="width/2 - 15" :y="height - 20" text-anchor="middle">0</text>
          <text :x="85" :y="height/2 + 20" text-anchor="middle">-1</text>
          <text :x="width-85" :y="height/2 + 20" text-anchor="middle">1</text>
          <text :x="width/2 + 15" :y="55" text-anchor="middle">1</text>
          <text :x="width/2 + 15" :y="height - 45" text-anchor="middle">-1</text>
          
          <!-- Axis titles -->
          <text :x="width - 40" :y="height/2 - 10" text-anchor="middle" class="text-base font-semibold">x</text>
        </g>
      </g>

      <!-- Polynomials -->
      <g>
        <!-- Visible polynomial paths -->
        <path
          v-for="polynomial in visiblePolynomials"
          :key="polynomial.degree"
          :d="polynomial.path"
          :stroke="polynomial.color"
          :stroke-width="getStrokeWidth(polynomial.degree)"
          :clip-path="`url(#polynomial-clip-${polynomial.degree})`"
          fill="none"
          :opacity="polynomial.opacity"
          class="polynomial-path transition-all duration-300 origin-center"
          :class="{
            'drop-shadow-lg scale-110': polynomial.degree === hoveredPolynomial,
            'filter brightness-110': polynomial.degree === hoveredPolynomial
          }"
          style="transform-origin: center center"
        />
        
        <!-- Invisible hover targets for full polynomial paths -->
        <path
          v-for="polynomial in visiblePolynomials"
          :key="`hover-${polynomial.degree}`"
          :d="polynomial.path"
          stroke="transparent"
          stroke-width="20"
          fill="none"
          class="cursor-pointer"
          @mouseenter="hoveredPolynomial = polynomial.degree"
          @mouseleave="hoveredPolynomial = null"
        />
      </g>

      <!-- Polynomial labels -->
      <g v-if="visiblePolynomials.length > 0">
        <foreignObject
          :x="width - 110"
          y="20"
          width="100"
          :height="Math.min(height - 40, visiblePolynomials.length * 30)"
        >
          <div class="flex flex-col gap-1">
            <div
              v-for="polynomial in visiblePolynomials"
              :key="`label-${polynomial.degree}`"
              class="cursor-pointer transition-all duration-200"
              @mouseenter="hoveredPolynomial = polynomial.degree"
              @mouseleave="hoveredPolynomial = null"
            >
              <LaTeX 
                :expression="`P_{${polynomial.degree}}(x)`"
                :style="{ 
                  color: polynomial.color,
                  fontSize: '18px',
                  fontWeight: polynomial.degree === hoveredPolynomial ? 'bold' : 'normal'
                }"
                class="transition-all duration-200"
              />
            </div>
          </div>
        </foreignObject>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { legendreApi, type LegendrePolynomial } from '@/utils/api'
import LaTeX from '@/components/custom/latex/LaTeX.vue'

interface Props {
  timePosition: number
  maxDegree: number
  width: number
  height: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'polynomial-hover': [degree: number | null]
}>()

const svgRef = ref<SVGSVGElement>()
const polynomials = ref<LegendrePolynomial[]>([])
const hoveredPolynomial = ref<number | null>(null)

// Computed properties
const currentDegree = computed(() => Math.floor(props.timePosition))

const visiblePolynomials = computed(() => {
  const result: any[] = []
  const maxVisible = Math.min(currentDegree.value + 1, polynomials.value.length)
  
  for (let i = 0; i < maxVisible; i++) {
    const polynomial = polynomials.value[i]
    if (!polynomial) continue
    
    const path = polynomialToPath(polynomial)
    
    // Calculate animation progress for this polynomial
    // Each polynomial starts animating when timePosition reaches its degree
    const animationStart = i
    const animationEnd = i + 1
    const progress = Math.max(0, Math.min(1, 
      (props.timePosition - animationStart) / (animationEnd - animationStart)
    ))
    
    // Calculate clip width to reveal polynomial from left to right
    // The graph spans from x=80 to x=width-80, so we need to map progress to this range
    const graphWidth = props.width - 160 // Total graph width (80px margins on each side)
    const clipWidth = 80 + (graphWidth * progress) // Start at 80px, extend by progress
    
    result.push({
      degree: i,
      path,
      color: getRainbowColor(i, props.maxDegree),
      opacity: i === currentDegree.value ? 1 : 0.6,
      clipWidth
    })
  }
  
  return result
})

// Helper functions
const getRainbowColor = (degree: number, maxDegree: number): string => {
  const hue = (degree / maxDegree) * 300 // Use 300 instead of 360 to avoid red overlap
  return `hsl(${hue}, 70%, 50%)`
}

const polynomialToPath = (polynomial: LegendrePolynomial): string => {
  const xScale = (props.width - 160) / 2
  const yScale = (props.height - 80) / 2
  const centerX = props.width / 2
  const centerY = props.height / 2

  const points = polynomial.x.map((x, i) => {
    const screenX = centerX + x * xScale
    const screenY = centerY - polynomial.y[i] * yScale
    return `${screenX},${screenY}`
  })

  return `M ${points.join(' L ')}`
}

const getStrokeWidth = (degree: number): number => {
  if (degree === hoveredPolynomial.value) return 5
  if (degree === currentDegree.value) return 3
  return 2
}


// Load polynomial data
const loadPolynomials = async () => {
  try {
    const data = await legendreApi.getPolynomialData(props.maxDegree)
    polynomials.value = data.polynomials || []
  } catch (error) {
    console.error('Failed to load polynomial data:', error)
    // Generate dummy data if API fails
    polynomials.value = Array.from({ length: props.maxDegree + 1 }, (_, degree) => ({
      degree,
      x: Array.from({ length: 200 }, (_, i) => -1 + 2 * i / 199),
      y: Array.from({ length: 200 }, (_, i) => {
        const x = -1 + 2 * i / 199
        // Simple approximation for demo
        return degree === 0 ? 1 : degree === 1 ? x : x ** degree
      })
    }))
  }
}

// Watch for changes
watch(() => props.maxDegree, loadPolynomials)
watch(hoveredPolynomial, (degree) => {
  emit('polynomial-hover', degree)
})

onMounted(() => {
  loadPolynomials()
})
</script>

<style scoped>
.polynomial-path {
  vector-effect: non-scaling-stroke;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.polynomial-path:hover {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2)) brightness(1.1);
}

.polynomial-label {
  transition: all 0.2s ease;
}
</style>