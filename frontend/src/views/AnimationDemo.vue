<template>
  <div class="animation-demo">
    <div class="container">
      <h1 class="title">3Blue1Brown Style Animations</h1>
      <p class="subtitle">Mathematical animation styles inspired by 3b1b's manim library</p>

      <!-- Animation Controls -->
      <div class="controls-section">
        <label>
          Animation Style:
          <select v-model="selectedStyle" @change="() => restartAnimation()">
            <option value="3b1b-radial">3b1b Radial (Circle Expand)</option>
            <option value="3b1b-diamond">3b1b Diamond</option>
            <option value="3b1b-morph">3b1b Morph (Ellipse)</option>
            <option value="center-out">Center Out (Original)</option>
            <option value="left-to-right">Left to Right</option>
            <option value="top-to-bottom">Top to Bottom</option>
          </select>
        </label>

        <label>
          Speed:
          <input 
            type="range" 
            v-model.number="animationSpeed" 
            min="0.5" 
            max="3" 
            step="0.1"
          />
          {{ animationSpeed }}s
        </label>

        <label>
          <input type="checkbox" v-model="autoplay" />
          Autoplay
        </label>

        <label>
          <input type="checkbox" v-model="loop" />
          Loop
        </label>
      </div>

      <!-- Demo Sections -->
      <div class="demo-grid">
        <!-- Basic Text Animation -->
        <div class="demo-card">
          <h3>Basic Text</h3>
          <LatexFillText
            ref="basicTextRef"
            content="E = mc²"
            :fillDirection="selectedStyle"
            :speed="animationSpeed"
            :autoplay="autoplay"
            :loop="loop"
            className="demo-text"
          />
          <div class="demo-controls">
            <button @click="playAnimation('basicText')">Play</button>
            <button @click="pauseAnimation('basicText')">Pause</button>
            <button @click="restartAnimation('basicText')">Restart</button>
          </div>
        </div>

        <!-- Mathematical Expression -->
        <div class="demo-card">
          <h3>Mathematical Expression</h3>
          <LatexFillText
            ref="mathTextRef"
            :latexExpression="'\\int_{-\\infty}^{\\infty} e^{-x^2} dx = \\sqrt{\\pi}'"
            :mathMode="true"
            :fillDirection="selectedStyle"
            :speed="animationSpeed"
            :autoplay="autoplay"
            :loop="loop"
            className="demo-text math-text"
          />
          <div class="demo-controls">
            <button @click="playAnimation('mathText')">Play</button>
            <button @click="pauseAnimation('mathText')">Pause</button>
            <button @click="restartAnimation('mathText')">Restart</button>
          </div>
        </div>

        <!-- Vector Notation -->
        <div class="demo-card">
          <h3>Vector Notation</h3>
          <LatexFillText
            ref="vectorTextRef"
            :latexExpression="'\\vec{v} = \\begin{pmatrix} x \\\\ y \\\\ z \\end{pmatrix}'"
            :mathMode="true"
            :fillDirection="selectedStyle"
            :speed="animationSpeed"
            :autoplay="autoplay"
            :loop="loop"
            className="demo-text math-text"
          />
          <div class="demo-controls">
            <button @click="playAnimation('vectorText')">Play</button>
            <button @click="pauseAnimation('vectorText')">Pause</button>
            <button @click="restartAnimation('vectorText')">Restart</button>
          </div>
        </div>

        <!-- Physics Equation -->
        <div class="demo-card">
          <h3>Physics Equation</h3>
          <LatexFillText
            ref="physicsTextRef"
            :latexExpression="'\\nabla \\times \\vec{B} = \\mu_0 \\vec{J} + \\mu_0 \\epsilon_0 \\frac{\\partial \\vec{E}}{\\partial t}'"
            :mathMode="true"
            :fillDirection="selectedStyle"
            :speed="animationSpeed"
            :autoplay="autoplay"
            :loop="loop"
            className="demo-text math-text"
          />
          <div class="demo-controls">
            <button @click="playAnimation('physicsText')">Play</button>
            <button @click="pauseAnimation('physicsText')">Pause</button>
            <button @click="restartAnimation('physicsText')">Restart</button>
          </div>
        </div>

        <!-- Calculus -->
        <div class="demo-card">
          <h3>Calculus</h3>
          <LatexFillText
            ref="calculusTextRef"
            :latexExpression="'\\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h} = f\'(x)'"
            :mathMode="true"
            :fillDirection="selectedStyle"
            :speed="animationSpeed"
            :autoplay="autoplay"
            :loop="loop"
            className="demo-text math-text"
          />
          <div class="demo-controls">
            <button @click="playAnimation('calculusText')">Play</button>
            <button @click="pauseAnimation('calculusText')">Pause</button>
            <button @click="restartAnimation('calculusText')">Restart</button>
          </div>
        </div>

        <!-- Linear Algebra -->
        <div class="demo-card">
          <h3>Linear Algebra</h3>
          <LatexFillText
            ref="linearTextRef"
            :latexExpression="'A = \\begin{bmatrix} a_{11} & a_{12} \\\\ a_{21} & a_{22} \\end{bmatrix}'"
            :mathMode="true"
            :fillDirection="selectedStyle"
            :speed="animationSpeed"
            :autoplay="autoplay"
            :loop="loop"
            className="demo-text math-text"
          />
          <div class="demo-controls">
            <button @click="playAnimation('linearText')">Play</button>
            <button @click="pauseAnimation('linearText')">Pause</button>
            <button @click="restartAnimation('linearText')">Restart</button>
          </div>
        </div>
      </div>

      <!-- Comparison Section -->
      <div class="comparison-section">
        <h2>Animation Style Comparison</h2>
        <div class="comparison-grid">
          <div 
            v-for="style in allStyles" 
            :key="style"
            class="comparison-item"
          >
            <h4>{{ getStyleName(style) }}</h4>
            <LatexFillText
              :content="'∇²φ = 0'"
              :fillDirection="style"
              :speed="1.5"
              :autoplay="false"
              :loop="true"
              className="comparison-text"
              @click="playComparisonAnimation(style)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import LatexFillText from '@/components/custom/text-animations/LatexFillText.vue'

// Animation refs
const basicTextRef = ref()
const mathTextRef = ref()
const vectorTextRef = ref()
const physicsTextRef = ref()
const calculusTextRef = ref()
const linearTextRef = ref()

// Animation settings
const selectedStyle = ref<string>('3b1b-radial')
const animationSpeed = ref(1.5)
const autoplay = ref(true)
const loop = ref(false)

// All available styles
const allStyles = [
  '3b1b-radial',
  '3b1b-diamond',
  '3b1b-morph',
  'center-out',
  'left-to-right',
  'top-to-bottom'
]

// Animation control methods
const playAnimation = (refName: string) => {
  const refs: Record<string, any> = {
    basicText: basicTextRef,
    mathText: mathTextRef,
    vectorText: vectorTextRef,
    physicsText: physicsTextRef,
    calculusText: calculusTextRef,
    linearText: linearTextRef,
  }
  
  refs[refName]?.value?.play()
}

const pauseAnimation = (refName: string) => {
  const refs: Record<string, any> = {
    basicText: basicTextRef,
    mathText: mathTextRef,
    vectorText: vectorTextRef,
    physicsText: physicsTextRef,
    calculusText: calculusTextRef,
    linearText: linearTextRef,
  }
  
  refs[refName]?.value?.pause()
}

const restartAnimation = (refName?: string) => {
  if (refName) {
    const refs: Record<string, any> = {
      basicText: basicTextRef,
      mathText: mathTextRef,
      vectorText: vectorTextRef,
      physicsText: physicsTextRef,
      calculusText: calculusTextRef,
      linearText: linearTextRef,
    }
    
    refs[refName]?.value?.restart()
  } else {
    // Restart all
    basicTextRef.value?.restart()
    mathTextRef.value?.restart()
    vectorTextRef.value?.restart()
    physicsTextRef.value?.restart()
    calculusTextRef.value?.restart()
    linearTextRef.value?.restart()
  }
}

const playComparisonAnimation = (style: string) => {
  // This would trigger the specific comparison animation
  console.log('Playing comparison animation:', style)
}

const getStyleName = (style: string) => {
  const names: Record<string, string> = {
    '3b1b-radial': '3b1b Radial',
    '3b1b-diamond': '3b1b Diamond',
    '3b1b-morph': '3b1b Morph',
    'center-out': 'Center Out',
    'left-to-right': 'Left to Right',
    'top-to-bottom': 'Top to Bottom',
  }
  return names[style] || style
}
</script>

<style scoped>
.animation-demo {
  min-height: 100vh;
  background: #0a0a0a;
  color: #fff;
  padding: 2rem;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
}

.title {
  font-size: 3rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 50%, #93c5fd 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 1.25rem;
  color: #94a3b8;
  margin-bottom: 3rem;
}

/* Controls Section */
.controls-section {
  background: #1a1a1a;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 3rem;
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
  align-items: center;
}

.controls-section label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #cbd5e1;
}

.controls-section select,
.controls-section input[type="range"] {
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 6px;
  padding: 0.5rem;
  color: #fff;
}

/* Demo Grid */
.demo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 2rem;
  margin-bottom: 4rem;
}

.demo-card {
  background: #1a1a1a;
  border-radius: 12px;
  padding: 2rem;
  border: 1px solid #2a2a2a;
  transition: all 0.3s ease;
}

.demo-card:hover {
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 10px 30px -10px rgba(59, 130, 246, 0.3);
}

.demo-card h3 {
  font-size: 1.25rem;
  margin-bottom: 1.5rem;
  color: #e2e8f0;
}

.demo-text {
  font-size: 2rem;
  font-weight: 600;
  display: block;
  text-align: center;
  margin: 2rem 0;
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.math-text {
  font-size: 1.5rem;
}

.demo-controls {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 1rem;
}

.demo-controls button {
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.demo-controls button:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

/* Comparison Section */
.comparison-section {
  margin-top: 4rem;
}

.comparison-section h2 {
  font-size: 2rem;
  margin-bottom: 2rem;
  color: #e2e8f0;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.comparison-item {
  background: #1a1a1a;
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid #2a2a2a;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
}

.comparison-item:hover {
  border-color: #3b82f6;
  background: #1e1e1e;
}

.comparison-item h4 {
  font-size: 0.875rem;
  color: #94a3b8;
  margin-bottom: 1rem;
}

.comparison-text {
  font-size: 1.5rem;
  font-weight: 600;
}

/* Responsive Design */
@media (max-width: 768px) {
  .demo-grid {
    grid-template-columns: 1fr;
  }
  
  .controls-section {
    flex-direction: column;
    align-items: stretch;
  }
  
  .title {
    font-size: 2rem;
  }
}
</style>