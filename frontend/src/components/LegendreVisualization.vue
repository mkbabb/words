<template>
  <div class="relative">
    <!-- Decorative header -->
    <div class="absolute -top-3 left-6 right-6 h-1 bg-gradient-to-r from-transparent via-primary to-transparent rounded-full opacity-60" />
    
    <ThemedCard variant="default" class="w-full relative overflow-hidden">
    <CardContent class="space-y-6">

      <!-- Tab Navigation -->
      <Tabs v-model="activeTab" class="w-full">
        <div class="flex justify-center mb-8 mt-6">
          <TabsList class="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="polynomials" class="text-base" style="font-family: 'Fraunces', serif;">Polynomial Animation</TabsTrigger>
            <TabsTrigger value="series" class="text-base" style="font-family: 'Fraunces', serif;">Series Approximation</TabsTrigger>
          </TabsList>
        </div>

        <!-- Polynomial Animation Tab -->
        <TabsContent 
          value="polynomials" 
          class="space-y-4 transition-all duration-300 ease-in-out"
          :class="{ 'opacity-100 translate-y-0': activeTab === 'polynomials', 'opacity-0 translate-y-2': activeTab !== 'polynomials' }"
        >
          <!-- Graph Section -->
          <div class="relative mb-6">
            <div class="bg-gradient-to-br from-background to-muted/10 rounded-xl p-6">
              <PolynomialCanvas
                :time-position="timePosition"
                :max-degree="maxDegree"
                :width="800"
                :height="500"
                @polynomial-hover="handlePolynomialHover"
              />
            </div>
          </div>
          
          <!-- Controls Section -->
          <div class="flex justify-center">
            <div class="max-w-4xl w-full">
              <div class="bg-gradient-to-br from-background to-muted/10 rounded-xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)] border-2 border-primary/20">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
                  <!-- Animation Speed -->
                  <div class="space-y-3">
                    <Label class="text-sm font-medium font-mono">Animation Speed</Label>
                    <Slider
                      v-model="animationSpeed"
                      :min="100"
                      :max="2000"
                      :step="100"
                      class="w-full"
                    />
                    <div class="text-xs text-muted-foreground text-center">{{ animationSpeed }}ms</div>
                  </div>
                  
                  <!-- Max Degree -->
                  <div class="space-y-3">
                    <Label class="text-sm font-medium font-mono">Max Degree</Label>
                    <Slider
                      v-model="maxDegree"
                      :min="5"
                      :max="25"
                      :step="1"
                      class="w-full"
                    />
                    <div class="text-xs text-muted-foreground text-center">
                      <LaTeX :expression="`P_0 \\text{ to } P_{${maxDegree}}`" />
                    </div>
                  </div>
                  
                  <!-- Time Position -->
                  <div class="space-y-3">
                    <div class="text-sm font-medium text-center">
                      <LaTeX :expression="`t`" />
                    </div>
                    <Slider
                      v-model="timePosition"
                      :min="0"
                      :max="maxDegree"
                      :step="0.1"
                      class="w-full"
                      @update:modelValue="onTimeChange"
                    />
                    <div class="flex justify-between text-sm text-muted-foreground items-center">
                      <LaTeX :expression="`P_0`" />
                      <LaTeX :expression="`P_{${Math.floor(timePosition)}}`" :style="{ color: getRainbowColor(Math.floor(timePosition), maxDegree), fontSize: '16px' }" />
                      <LaTeX :expression="`P_{${maxDegree}}`" />
                    </div>
                  </div>
                </div>
                
                <!-- Play/Pause Controls -->
                <div class="flex justify-center mt-4 pt-3 border-t border-muted/20">
                  <div class="flex items-center gap-6">
                    <button
                      @click="toggleAnimation"
                      class="p-3 rounded-full hover:bg-primary/10 transition-colors duration-200 group"
                      :title="isAnimating ? 'Pause Animation' : 'Play Animation'"
                    >
                      <Play v-if="!isAnimating" class="h-6 w-6 text-primary group-hover:scale-110 transition-transform" />
                      <Pause v-else class="h-6 w-6 text-primary group-hover:scale-110 transition-transform" />
                    </button>
                    <button
                      @click="resetAnimation"
                      class="p-3 rounded-full hover:bg-muted/50 transition-colors duration-200 group"
                      title="Reset Animation"
                    >
                      <RotateCcw class="h-6 w-6 text-muted-foreground group-hover:scale-110 transition-transform" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        <!-- Series Approximation Tab -->
        <TabsContent 
          value="series" 
          class="space-y-6 transition-all duration-300 ease-in-out"
          :class="{ 'opacity-100 translate-y-0': activeTab === 'series', 'opacity-0 translate-y-2': activeTab !== 'series' }"
        >
          <SeriesApproximation
            :harmonics="harmonics"
            @harmonics-change="harmonics = $event"
          />
        </TabsContent>
      </Tabs>
    </CardContent>
    </ThemedCard>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { Play, Pause, RotateCcw } from 'lucide-vue-next'

import ThemedCard from '@/components/ui/ThemedCard.vue'
import CardContent from '@/components/ui/CardContent.vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Label from '@/components/ui/Label.vue'
import Slider from '@/components/ui/Slider.vue'
import PolynomialCanvas from './PolynomialCanvas.vue'
import SeriesApproximation from './SeriesApproximation.vue'
import LaTeX from '@/components/custom/latex/LaTeX.vue'

// Reactive state
const activeTab = ref<'polynomials' | 'series'>('polynomials')
const animationSpeed = ref(500)
const maxDegree = ref(15)
const harmonics = ref(20)
const timePosition = ref(0)
const isAnimating = ref(false)
// Animation control
let animationInterval: number | undefined

// Animation functions
const toggleAnimation = () => {
  isAnimating.value = !isAnimating.value
  if (isAnimating.value) {
    startAnimation()
  } else {
    stopAnimation()
  }
}

const startAnimation = () => {
  if (animationInterval) clearInterval(animationInterval)
  
  animationInterval = window.setInterval(() => {
    if (timePosition.value >= maxDegree.value) {
      timePosition.value = 0
    } else {
      timePosition.value += 0.1
    }
  }, animationSpeed.value / 10)
}

const stopAnimation = () => {
  if (animationInterval) {
    clearInterval(animationInterval)
    animationInterval = undefined
  }
}

const resetAnimation = () => {
  stopAnimation()
  timePosition.value = 0
  isAnimating.value = false
}

const onTimeChange = () => {
  if (isAnimating.value) {
    stopAnimation()
    isAnimating.value = false
  }
}


// Watch for animation speed changes
watch(animationSpeed, () => {
  if (isAnimating.value) {
    stopAnimation()
    startAnimation()
  }
})

// Watch for max degree changes
watch(maxDegree, () => {
  if (timePosition.value > maxDegree.value) {
    timePosition.value = maxDegree.value
  }
})

// Helper function for rainbow colors
const getRainbowColor = (degree: number, maxDegree: number): string => {
  const hue = (degree / maxDegree) * 300 // Use 300 instead of 360 to avoid red overlap
  return `hsl(${hue}, 70%, 50%)`
}

const handlePolynomialHover = (degree: number | null) => {
  // Handle polynomial hover highlighting
  console.log('Hovering polynomial:', degree)
}

onMounted(() => {
  // Start with a brief animation
  setTimeout(() => {
    isAnimating.value = true
    startAnimation()
  }, 1000)
})

onUnmounted(() => {
  stopAnimation()
})
</script>