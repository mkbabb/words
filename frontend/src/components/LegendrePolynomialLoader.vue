<template>
  <Card>
    <CardContent class="p-6">
      <div ref="containerRef" class="relative">
        <svg
          ref="svgRef"
          :width="width"
          :height="height"
          class="w-full h-full"
          :viewBox="`0 0 ${width} ${height}`"
        >
          <defs>
            <clipPath id="graph-clip">
              <rect x="0" y="0" :width="width" :height="height" />
            </clipPath>
            <linearGradient id="grid-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stop-color="currentColor" stop-opacity="0.1" />
              <stop offset="100%" stop-color="currentColor" stop-opacity="0.05" />
            </linearGradient>
          </defs>
          
          <!-- Grid lines -->
          <g class="text-muted-foreground/20">
            <!-- Vertical grid lines -->
            <line v-for="i in 11" :key="`v-${i}`"
              :x1="(i - 1) * width / 10"
              :y1="0"
              :x2="(i - 1) * width / 10"
              :y2="height"
              stroke="currentColor"
              stroke-width="0.5"
            />
            <!-- Horizontal grid lines -->
            <line v-for="i in 5" :key="`h-${i}`"
              :x1="0"
              :y1="(i - 1) * height / 4"
              :x2="width"
              :y2="(i - 1) * height / 4"
              stroke="currentColor"
              stroke-width="0.5"
            />
          </g>
          
          <!-- Axes -->
          <g class="text-foreground">
            <line :x1="width/2" :y1="0" :x2="width/2" :y2="height" stroke="currentColor" stroke-width="1" opacity="0.3" />
            <line :x1="0" :y1="height/2" :x2="width" :y2="height/2" stroke="currentColor" stroke-width="1" opacity="0.3" />
          </g>
          
          <!-- Polynomials -->
          <g clip-path="url(#graph-clip)">
            <path
              v-for="polynomial in visiblePolynomials"
              :key="polynomial.degree"
              :d="polynomial.path"
              :stroke="polynomial.color"
              :stroke-width="2.5"
              fill="none"
              :opacity="polynomial.opacity"
              class="polynomial-path transition-opacity duration-300"
            />
          </g>
          
          <!-- Degree labels -->
          <g v-if="visiblePolynomials.length > 0" class="text-xs fill-muted-foreground">
            <text
              v-for="polynomial in visiblePolynomials.slice(-3)"
              :key="`label-${polynomial.degree}`"
              :x="width - 10"
              :y="20 + polynomial.degree * 15"
              text-anchor="end"
              :fill="polynomial.color"
              :opacity="polynomial.opacity"
            >
              P₍{{ polynomial.degree }}₎
            </text>
          </g>
        </svg>
        
        <!-- Loading indicator -->
        <div v-if="currentDegree <= maxDegree && running" class="absolute bottom-2 right-2">
          <div class="flex items-center gap-2 text-xs text-muted-foreground">
            <div class="h-2 w-2 rounded-full bg-primary animate-pulse" />
            <span>Loading P₍{{ currentDegree }}₎</span>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { gsap } from 'gsap';
import { legendreApi, type LegendrePolynomial } from '@/utils/api';
import Card from '@/components/ui/Card.vue';
import CardContent from '@/components/ui/CardContent.vue';

interface Props {
  height?: number;
  interval?: number;
  maxDegree?: number;
  running?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  height: 160, // 10rem = 160px
  interval: 500, // 0.5s
  maxDegree: 10,
  running: true
});

const containerRef = ref<HTMLDivElement>();
const svgRef = ref<SVGSVGElement>();
const width = ref(400);
const polynomials = ref<LegendrePolynomial[]>([]);
const currentDegree = ref(0);
const visiblePolynomials = ref<any[]>([]);

let addPolynomialInterval: number | undefined;

const height = computed(() => props.height);

// Generate rainbow colors
const getRainbowColor = (degree: number, maxDegree: number): string => {
  const hue = (degree / maxDegree) * 360;
  return `hsl(${hue}, 70%, 50%)`;
};

// Convert polynomial data to SVG path
const polynomialToPath = (polynomial: LegendrePolynomial): string => {
  const xScale = width.value / 2;
  const yScale = height.value / 4; // Adjusted for better visibility
  const centerY = height.value / 2;

  const points = polynomial.x.map((x, i) => {
    const screenX = (x + 1) * xScale;
    const screenY = centerY - polynomial.y[i] * yScale;
    return `${screenX},${screenY}`;
  });

  return `M ${points.join(' L ')}`;
};

// Add a new polynomial with animation
const addPolynomial = async () => {
  if (currentDegree.value > props.maxDegree) {
    return;
  }

  // Find polynomial data for current degree
  const polynomial = polynomials.value.find(p => p.degree === currentDegree.value);
  if (!polynomial) return;

  const newPoly = {
    degree: currentDegree.value,
    path: polynomialToPath(polynomial),
    color: getRainbowColor(currentDegree.value, props.maxDegree),
    opacity: 0
  };

  visiblePolynomials.value.push(newPoly);

  // Animate the new polynomial
  gsap.to(newPoly, {
    opacity: 1,
    duration: 0.8,
    ease: "circ.out"
  });

  // Animate path drawing effect
  const pathElement = svgRef.value?.querySelector(`.polynomial-path:last-child`) as SVGPathElement;
  if (pathElement) {
    const length = pathElement.getTotalLength();
    gsap.set(pathElement, {
      strokeDasharray: length,
      strokeDashoffset: length
    });
    gsap.to(pathElement, {
      strokeDashoffset: 0,
      duration: 1.2,
      ease: "circ.inOut"
    });
  }

  currentDegree.value++;
};

// Update container width based on search bar
const updateWidth = () => {
  if (containerRef.value) {
    // Match search bar width
    const searchBar = document.querySelector('.search-container');
    if (searchBar) {
      width.value = searchBar.clientWidth;
    }
  }
};

// Load polynomial data
const loadPolynomials = async () => {
  try {
    const data = await legendreApi.getPolynomialData(props.maxDegree);
    polynomials.value = data.polynomials;
    
    // Start animation sequence
    if (props.running) {
      startAnimation();
    }
  } catch (error) {
    console.error('Failed to load polynomial data:', error);
  }
};

// Start/stop animation
const startAnimation = () => {
  if (addPolynomialInterval) {
    clearInterval(addPolynomialInterval);
  }
  
  addPolynomialInterval = window.setInterval(() => {
    if (currentDegree.value <= props.maxDegree) {
      addPolynomial();
    } else {
      stopAnimation();
    }
  }, props.interval);
};

const stopAnimation = () => {
  if (addPolynomialInterval) {
    clearInterval(addPolynomialInterval);
    addPolynomialInterval = undefined;
  }
};

// Reset animation
const reset = () => {
  stopAnimation();
  currentDegree.value = 0;
  visiblePolynomials.value = [];
  if (props.running) {
    startAnimation();
  }
};

// Watch for running prop changes
watch(() => props.running, (newVal) => {
  if (newVal) {
    startAnimation();
  } else {
    stopAnimation();
  }
});

onMounted(() => {
  updateWidth();
  window.addEventListener('resize', updateWidth);
  loadPolynomials();
});

onUnmounted(() => {
  stopAnimation();
  window.removeEventListener('resize', updateWidth);
});

// Expose methods for parent components
defineExpose({
  reset,
  startAnimation,
  stopAnimation
});
</script>

<style scoped>
.polynomial-path {
  vector-effect: non-scaling-stroke;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.polynomial-path:hover {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}
</style>