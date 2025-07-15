<template>
  <div class="relative">
    <!-- Decorative header -->
    <div
      class="via-primary absolute -top-3 right-6 left-6 h-1 rounded-full bg-gradient-to-r from-transparent to-transparent opacity-60"
    />

    <ThemedCard variant="default" class="relative w-full overflow-hidden">
      <CardContent class="space-y-6">
        <!-- Tab Navigation -->
        <Tabs v-model="activeTab" class="w-full">
          <div class="mt-6 mb-8 flex justify-center">
            <TabsList class="grid w-full max-w-md grid-cols-2">
              <TabsTrigger
                value="polynomials"
                class="text-base"
                style="font-family: 'Fraunces', serif"
                >Polynomial Animation</TabsTrigger
              >
              <TabsTrigger
                value="series"
                class="text-base"
                style="font-family: 'Fraunces', serif"
                >Series Approximation</TabsTrigger
              >
            </TabsList>
          </div>

          <!-- Polynomial Animation Tab -->
          <TabsContent
            value="polynomials"
            class="space-y-4 transition-all duration-300 ease-in-out"
            :class="{
              'translate-y-0 opacity-100': activeTab === 'polynomials',
              'translate-y-2 opacity-0': activeTab !== 'polynomials',
            }"
          >
            <!-- Graph Section -->
            <div class="relative mb-6">
              <div
                class="from-background to-muted/10 rounded-xl bg-gradient-to-br p-12"
              >
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
              <div class="w-full max-w-4xl">
                <div
                  class="from-background to-muted/10 border-primary/20 rounded-xl border-2 bg-gradient-to-br p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)]"
                >
                  <div
                    class="grid grid-cols-1 items-center gap-6 md:grid-cols-3"
                  >
                    <!-- Animation Speed -->
                    <div class="space-y-3">
                      <Label class="font-mono text-sm font-medium"
                        >Animation Speed</Label
                      >
                      <Slider
                        v-model="animationSpeed"
                        :min="100"
                        :max="2000"
                        :step="100"
                        class="w-full"
                      />
                      <div class="text-muted-foreground text-center text-xs">
                        {{ animationSpeed }}ms
                      </div>
                    </div>

                    <!-- Max Degree -->
                    <div class="space-y-3">
                      <Label class="font-mono text-sm font-medium"
                        >Max Degree</Label
                      >
                      <Slider
                        v-model="maxDegree"
                        :min="5"
                        :max="25"
                        :step="1"
                        class="w-full"
                      />
                      <div class="text-muted-foreground text-center text-xs">
                        <LaTeX
                          :expression="`P_0 \\text{ to } P_{${maxDegree}}`"
                        />
                      </div>
                    </div>

                    <!-- Time Position -->
                    <div class="space-y-3">
                      <div class="text-center text-sm font-medium">
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
                      <div
                        class="text-muted-foreground flex items-center justify-between text-sm"
                      >
                        <LaTeX :expression="`P_0`" />
                        <LaTeX
                          :expression="`P_{${Math.floor(timePosition)}}`"
                          :style="{
                            color: getRainbowColor(
                              Math.floor(timePosition),
                              maxDegree
                            ),
                            fontSize: '16px',
                          }"
                        />
                        <LaTeX :expression="`P_{${maxDegree}}`" />
                      </div>
                    </div>
                  </div>

                  <!-- Play/Pause Controls -->
                  <div
                    class="border-muted/20 mt-4 flex justify-center border-t pt-3"
                  >
                    <div class="flex items-center gap-6">
                      <button
                        @click="toggleAnimation"
                        class="hover:bg-primary/10 group rounded-full p-3 transition-colors duration-200"
                        :title="
                          isAnimating ? 'Pause Animation' : 'Play Animation'
                        "
                      >
                        <Play
                          v-if="!isAnimating"
                          class="text-primary h-6 w-6 transition-transform group-hover:scale-110"
                        />
                        <Pause
                          v-else
                          class="text-primary h-6 w-6 transition-transform group-hover:scale-110"
                        />
                      </button>
                      <button
                        @click="resetAnimation"
                        class="hover:bg-muted/50 group rounded-full p-3 transition-colors duration-200"
                        title="Reset Animation"
                      >
                        <RotateCcw
                          class="text-muted-foreground h-6 w-6 transition-transform group-hover:scale-110"
                        />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </ThemedCard>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { Play, Pause, RotateCcw } from 'lucide-vue-next';

import ThemedCard from '@/components/ui/ThemedCard.vue';
import CardContent from '@/components/ui/CardContent.vue';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Label from '@/components/ui/Label.vue';
import Slider from '@/components/ui/Slider.vue';
import PolynomialCanvas from './PolynomialCanvas.vue';

import LaTeX from '@/components/custom/latex/LaTeX.vue';

// Reactive state
const activeTab = ref<'polynomials' | 'series'>('polynomials');
const animationSpeed = ref(500);
const maxDegree = ref(15);
const timePosition = ref(0);
const isAnimating = ref(false);
// Animation control
let animationInterval: number | undefined;

// Animation functions
const toggleAnimation = () => {
  isAnimating.value = !isAnimating.value;
  if (isAnimating.value) {
    startAnimation();
  } else {
    stopAnimation();
  }
};

const startAnimation = () => {
  if (animationInterval) clearInterval(animationInterval);

  animationInterval = window.setInterval(() => {
    if (timePosition.value >= maxDegree.value) {
      timePosition.value = 0;
    } else {
      timePosition.value += 0.1;
    }
  }, animationSpeed.value / 10);
};

const stopAnimation = () => {
  if (animationInterval) {
    clearInterval(animationInterval);
    animationInterval = undefined;
  }
};

const resetAnimation = () => {
  stopAnimation();
  timePosition.value = 0;
  isAnimating.value = false;
};

const onTimeChange = () => {
  if (isAnimating.value) {
    stopAnimation();
    isAnimating.value = false;
  }
};

// Watch for animation speed changes
watch(animationSpeed, () => {
  if (isAnimating.value) {
    stopAnimation();
    startAnimation();
  }
});

// Watch for max degree changes
watch(maxDegree, () => {
  if (timePosition.value > maxDegree.value) {
    timePosition.value = maxDegree.value;
  }
});

// Helper function for rainbow colors
const getRainbowColor = (degree: number, maxDegree: number): string => {
  const hue = (degree / maxDegree) * 300; // Use 300 instead of 360 to avoid red overlap
  return `hsl(${hue}, 70%, 50%)`;
};

const handlePolynomialHover = (degree: number | null) => {
  // Handle polynomial hover highlighting
  console.log('Hovering polynomial:', degree);
};

onMounted(() => {
  // Start with a brief animation
  setTimeout(() => {
    isAnimating.value = true;
    startAnimation();
  }, 1000);
});

onUnmounted(() => {
  stopAnimation();
});
</script>
