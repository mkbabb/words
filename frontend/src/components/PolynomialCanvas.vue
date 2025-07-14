<template>
  <div class="relative">
    <svg
      ref="svgRef"
      :width="width"
      :height="height"
      class="from-background to-muted/20 h-auto w-full rounded-lg border bg-gradient-to-br"
      :viewBox="`0 0 ${width} ${height}`"
      @mouseleave="hoveredPolynomial = null"
    >
      <defs>
        <!-- Grid pattern -->
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path
            d="M 40 0 L 0 0 0 40"
            fill="none"
            stroke="currentColor"
            stroke-width="0.5"
            stroke-dasharray="2,2"
            class="text-muted-foreground/20"
          />
        </pattern>

        <!-- Gradient for axes -->
        <linearGradient id="axisGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="currentColor" stop-opacity="0.1" />
          <stop offset="50%" stop-color="currentColor" stop-opacity="0.3" />
          <stop offset="100%" stop-color="currentColor" stop-opacity="0.1" />
        </linearGradient>

        <!-- Clipping paths for polynomial animation -->
        <clipPath
          v-for="polynomial in visiblePolynomials"
          :key="`clip-${polynomial.degree}`"
          :id="`polynomial-clip-${polynomial.degree}`"
        >
          <rect
            :x="graphBounds.left"
            y="0"
            :width="polynomial.clipWidth"
            :height="height"
          />
        </clipPath>
      </defs>

      <!-- Grid background -->
      <rect
        width="100%"
        height="100%"
        fill="url(#grid)"
        stroke-dasharray="2,2"
      />

      <!-- Coordinate system -->
      <g class="text-foreground">
        <!-- Main axes -->
        <defs>
          <marker
            id="arrowX"
            markerWidth="10"
            markerHeight="10"
            refX="8"
            refY="3"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <polygon points="0,0 0,6 9,3" fill="currentColor" />
          </marker>
          <marker
            id="arrowY"
            markerWidth="8"
            markerHeight="8"
            refX="8"
            refY="3"
            orient="270"
            markerUnits="strokeWidth"
          >
            <polygon points="0,0 0,6 9,3" fill="currentColor" />
          </marker>
        </defs>

        <!-- Y-axis (arrow points down) -->
        <line
          :x1="graphCenter.x"
          :y1="graphBounds.bottom"
          :x2="graphCenter.x"
          :y2="graphBounds.top"
          stroke="currentColor"
          stroke-width="3"
          marker-end="url(#arrowY)"
        />
        <!-- X-axis -->
        <line
          :x1="graphBounds.left"
          :y1="graphCenter.y"
          :x2="graphBounds.right"
          :y2="graphCenter.y"
          stroke="currentColor"
          stroke-width="3"
          marker-end="url(#arrowX)"
        />

        <!-- Tick marks -->
        <g stroke="currentColor" stroke-width="2">
          <!-- X-axis ticks -->
          <line
            :x1="graphBounds.left"
            :y1="graphCenter.y - 8"
            :x2="graphBounds.left"
            :y2="graphCenter.y + 8"
          />
          <line
            :x1="graphBounds.right"
            :y1="graphCenter.y - 8"
            :x2="graphBounds.right"
            :y2="graphCenter.y + 8"
          />
          <line
            :x1="graphBounds.left + graphBounds.width * 0.25"
            :y1="graphCenter.y - 5"
            :x2="graphBounds.left + graphBounds.width * 0.25"
            :y2="graphCenter.y + 5"
          />
          <line
            :x1="graphBounds.left + graphBounds.width * 0.75"
            :y1="graphCenter.y - 5"
            :x2="graphBounds.left + graphBounds.width * 0.75"
            :y2="graphCenter.y + 5"
          />

          <!-- Y-axis ticks -->
          <line
            :x1="graphCenter.x - 8"
            :y1="graphBounds.top"
            :x2="graphCenter.x + 8"
            :y2="graphBounds.top"
          />
          <line
            :x1="graphCenter.x - 8"
            :y1="graphBounds.bottom"
            :x2="graphCenter.x + 8"
            :y2="graphBounds.bottom"
          />
          <line
            :x1="graphCenter.x - 5"
            :y1="graphBounds.top + graphBounds.height * 0.25"
            :x2="graphCenter.x + 5"
            :y2="graphBounds.top + graphBounds.height * 0.25"
          />
          <line
            :x1="graphCenter.x - 5"
            :y1="graphBounds.top + graphBounds.height * 0.75"
            :x2="graphCenter.x + 5"
            :y2="graphBounds.top + graphBounds.height * 0.75"
          />
        </g>

        <!-- Axis labels -->
        <g>
          <!-- X-axis labels -->
          <foreignObject
            :x="graphCenter.x - 10"
            :y="height - 25"
            width="20"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="0" style="font-size: 14px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphBounds.left - 10"
            :y="graphCenter.y + 10"
            width="20"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="-1" style="font-size: 14px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphBounds.right - 10"
            :y="graphCenter.y + 10"
            width="20"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="1" style="font-size: 14px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphBounds.left + graphBounds.width * 0.25 - 15"
            :y="graphCenter.y + 10"
            width="30"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="-0.5" style="font-size: 12px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphBounds.left + graphBounds.width * 0.75 - 15"
            :y="graphCenter.y + 10"
            width="30"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="0.5" style="font-size: 12px" />
            </div>
          </foreignObject>

          <!-- Y-axis labels -->
          <foreignObject
            :x="graphCenter.x + 15"
            :y="graphBounds.top - 5"
            width="25"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="1" style="font-size: 14px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphCenter.x + 15"
            :y="graphBounds.bottom - 10"
            width="25"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="-1" style="font-size: 14px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphCenter.x + 15"
            :y="graphBounds.top + graphBounds.height * 0.25 - 7"
            width="30"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="0.5" style="font-size: 12px" />
            </div>
          </foreignObject>
          <foreignObject
            :x="graphCenter.x + 15"
            :y="graphBounds.top + graphBounds.height * 0.75 - 7"
            width="30"
            height="15"
          >
            <div class="flex h-full items-center justify-center">
              <LaTeX expression="-0.5" style="font-size: 12px" />
            </div>
          </foreignObject>

          <!-- Axis title -->
          <foreignObject :x="graphBounds.right" :y="graphCenter.y + 32">
            <LaTeX expression="x" class="text-4xl" />
          </foreignObject>

          <foreignObject :x="graphCenter.x" :y="graphBounds.top">
            <LaTeX expression="y" class="text-4xl" />
          </foreignObject>
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
          class="polynomial-path origin-center transition-all duration-300"
          :class="{
            'scale-110 drop-shadow-lg': polynomial.degree === hoveredPolynomial,
            'brightness-110 filter': polynomial.degree === hoveredPolynomial,
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
          :x="graphBounds.right + 10"
          :y="graphBounds.top"
          :width="graphPadding.right - 20"
          :height="Math.min(graphBounds.height, visiblePolynomials.length * 30)"
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
                  fontWeight:
                    polynomial.degree === hoveredPolynomial ? 'bold' : 'normal',
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
import { ref, computed, watch, onMounted } from 'vue';
import { legendreApi, type LegendrePolynomial } from '@/utils/api';
import LaTeX from '@/components/custom/latex/LaTeX.vue';

interface Props {
  timePosition: number;
  maxDegree: number;
  width: number;
  height: number;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  'polynomial-hover': [degree: number | null];
}>();

const svgRef = ref<SVGSVGElement>();
const polynomials = ref<LegendrePolynomial[]>([]);
const hoveredPolynomial = ref<number | null>(null);

// Graph layout constants
const graphPadding = computed(() => ({
  top: 0,
  right: 0,
  bottom: 0,
  left: 0,
}));

const graphBounds = computed(() => ({
  left: graphPadding.value.left,
  right: props.width - graphPadding.value.right,
  top: graphPadding.value.top,
  bottom: props.height - graphPadding.value.bottom,
  width: props.width - graphPadding.value.left - graphPadding.value.right,
  height: props.height - graphPadding.value.top - graphPadding.value.bottom,
}));

const graphCenter = computed(() => ({
  x: props.width / 2,
  y: props.height / 2,
}));

const graphScale = computed(() => ({
  x: graphBounds.value.width / 2,
  y: graphBounds.value.height / 2,
}));

// Computed properties
const currentDegree = computed(() => Math.floor(props.timePosition));

const visiblePolynomials = computed(() => {
  const result: any[] = [];
  const maxVisible = Math.min(
    currentDegree.value + 1,
    polynomials.value.length
  );

  for (let i = 0; i < maxVisible; i++) {
    const polynomial = polynomials.value[i];
    if (!polynomial) continue;

    const path = polynomialToPath(polynomial);

    // Calculate animation progress for this polynomial
    // Each polynomial starts animating when timePosition reaches its degree
    const animationStart = i;
    const animationEnd = i + 1;
    const progress = Math.max(
      0,
      Math.min(
        1,
        (props.timePosition - animationStart) / (animationEnd - animationStart)
      )
    );

    // Calculate clip width to reveal polynomial from left to right
    const clipWidth =
      graphBounds.value.left + graphBounds.value.width * progress;

    result.push({
      degree: i,
      path,
      color: getRainbowColor(i, props.maxDegree),
      opacity: i === currentDegree.value ? 1 : 0.6,
      clipWidth,
    });
  }

  return result;
});

// Helper functions
const getRainbowColor = (degree: number, maxDegree: number): string => {
  const hue = (degree / maxDegree) * 300; // Use 300 instead of 360 to avoid red overlap
  return `hsl(${hue}, 70%, 50%)`;
};

const polynomialToPath = (polynomial: LegendrePolynomial): string => {
  const points = polynomial.x.map((x, i) => {
    const screenX = graphCenter.value.x + x * graphScale.value.x;
    const screenY = graphCenter.value.y - polynomial.y[i] * graphScale.value.y;
    return `${screenX},${screenY}`;
  });

  return `M ${points.join(' L ')}`;
};

const getStrokeWidth = (degree: number): number => {
  if (degree === hoveredPolynomial.value) return 5;
  if (degree === currentDegree.value) return 3;
  return 2;
};

// Load polynomial data
const loadPolynomials = async () => {
  try {
    const data = await legendreApi.getPolynomialData(props.maxDegree);
    polynomials.value = data.polynomials || [];
  } catch (error) {
    console.error('Failed to load polynomial data:', error);
    // Generate dummy data if API fails
    polynomials.value = Array.from(
      { length: props.maxDegree + 1 },
      (_, degree) => ({
        degree,
        x: Array.from({ length: 200 }, (_, i) => -1 + (2 * i) / 199),
        y: Array.from({ length: 200 }, (_, i) => {
          const x = -1 + (2 * i) / 199;
          // Simple approximation for demo
          return degree === 0 ? 1 : degree === 1 ? x : x ** degree;
        }),
      })
    );
  }
};

// Watch for changes
watch(() => props.maxDegree, loadPolynomials);
watch(hoveredPolynomial, degree => {
  emit('polynomial-hover', degree);
});

onMounted(() => {
  loadPolynomials();
});
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
