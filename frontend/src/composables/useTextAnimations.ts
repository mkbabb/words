import { ref, onMounted, onUnmounted, nextTick, type Ref } from 'vue'
import { gsap } from 'gsap'
import type { TypewriterOptions, HandwritingOptions, LatexFillOptions } from '@/types'

/**
 * Composable for text animation systems using GSAP
 * Provides typewriter, handwriting, and LaTeX fill animations
 */

// Typewriter animation composable
export function useTypewriterAnimation(
  elementRef: Ref<HTMLElement | null>,
  text: Ref<string>,
  options: Partial<TypewriterOptions> = {}
) {
  const isAnimating = ref(false)
  const currentText = ref('')
  const cursorVisible = ref(true)
  let timeline: gsap.core.Timeline | null = null
  let cursorTimeline: gsap.core.Timeline | null = null

  const defaultOptions: TypewriterOptions = {
    speed: 50, // characters per second
    delay: 0,
    autoplay: true,
    loop: false,
    easing: 'none',
    cursorVisible: true,
    cursorChar: '|',
    pauseOnPunctuation: 200, // ms pause after punctuation
  }

  const config = { ...defaultOptions, ...options }

  const startAnimation = async () => {
    if (!elementRef.value || isAnimating.value) return

    isAnimating.value = true
    currentText.value = ''
    
    await nextTick()

    // Create main timeline
    timeline = gsap.timeline({
      paused: !config.autoplay,
      delay: config.delay / 1000,
      repeat: config.loop ? -1 : 0,
    })

    const chars = text.value.split('')
    const charDuration = 1 / config.speed

    chars.forEach((char, index) => {
      timeline!.call(() => {
        currentText.value = text.value.slice(0, index + 1)
        if (elementRef.value) {
          elementRef.value.textContent = currentText.value + (config.cursorVisible ? config.cursorChar : '')
        }
      })

      // Add pause after punctuation
      const isPunctuation = /[.!?,:;]/.test(char)
      const delay = isPunctuation ? config.pauseOnPunctuation / 1000 : 0

      timeline!.to({}, { duration: charDuration + delay })
    })

    // Remove cursor at end
    timeline.call(() => {
      if (elementRef.value && config.cursorVisible) {
        elementRef.value.textContent = currentText.value
      }
      isAnimating.value = false
    })

    if (config.autoplay) {
      timeline.play()
    }
  }

  const startCursorBlink = () => {
    if (!config.cursorVisible) return
    
    cursorTimeline = gsap.timeline({ repeat: -1, yoyo: true })
    cursorTimeline.to(cursorVisible, { 
      duration: 0.5, 
      delay: 0.5,
      onUpdate: () => {
        if (elementRef.value && isAnimating.value) {
          const cursor = cursorVisible.value ? config.cursorChar : ''
          elementRef.value.textContent = currentText.value + cursor
        }
      }
    })
  }

  const play = () => timeline?.play()
  const pause = () => timeline?.pause()
  const restart = () => {
    timeline?.restart()
    startAnimation()
  }

  const cleanup = () => {
    timeline?.kill()
    cursorTimeline?.kill()
    timeline = null
    cursorTimeline = null
  }

  onMounted(() => {
    if (config.autoplay) {
      startAnimation()
    }
    startCursorBlink()
  })

  onUnmounted(cleanup)

  return {
    isAnimating,
    currentText,
    startAnimation,
    play,
    pause,
    restart,
    cleanup,
  }
}

// Handwriting animation composable
export function useHandwritingAnimation(
  pathRef: Ref<SVGPathElement | null>,
  options: Partial<HandwritingOptions> = {}
) {
  const isAnimating = ref(false)
  let timeline: gsap.core.Timeline | null = null

  const defaultOptions: HandwritingOptions = {
    speed: 1,
    delay: 0,
    autoplay: true,
    loop: false,
    easing: 'none',
    strokeWidth: 2,
    pressure: 0.8,
    style: 'pen',
  }

  const config = { ...defaultOptions, ...options }

  const startAnimation = async () => {
    if (!pathRef.value || isAnimating.value) return

    isAnimating.value = true
    const path = pathRef.value
    const pathLength = path.getTotalLength()

    // Set up path for animation
    gsap.set(path, {
      strokeDasharray: pathLength,
      strokeDashoffset: pathLength,
      strokeWidth: config.strokeWidth,
      opacity: config.pressure,
    })

    // Add texture class based on style
    path.classList.add(`handwriting-${config.style}`)

    timeline = gsap.timeline({
      paused: !config.autoplay,
      delay: config.delay / 1000,
      repeat: config.loop ? -1 : 0,
      onComplete: () => {
        isAnimating.value = false
      },
    })

    timeline.to(path, {
      strokeDashoffset: 0,
      duration: config.speed,
      ease: config.easing,
    })

    if (config.autoplay) {
      timeline.play()
    }
  }

  const play = () => timeline?.play()
  const pause = () => timeline?.pause()
  const restart = () => {
    timeline?.restart()
    startAnimation()
  }

  const cleanup = () => {
    timeline?.kill()
    timeline = null
  }

  onMounted(() => {
    if (config.autoplay) {
      startAnimation()
    }
  })

  onUnmounted(cleanup)

  return {
    isAnimating,
    startAnimation,
    play,
    pause,
    restart,
    cleanup,
  }
}

// LaTeX fill animation composable
export function useLatexFillAnimation(
  elementRef: Ref<HTMLElement | null>,
  options: Partial<LatexFillOptions> = {}
) {
  const isAnimating = ref(false)
  let timeline: gsap.core.Timeline | null = null

  const defaultOptions: LatexFillOptions = {
    speed: 1,
    delay: 0,
    autoplay: true,
    loop: false,
    easing: 'power2.inOut',
    fillDirection: 'left-to-right',
    mathMode: true,
  }

  const config = { ...defaultOptions, ...options }

  const startAnimation = async () => {
    if (!elementRef.value || isAnimating.value) return

    isAnimating.value = true
    const element = elementRef.value

    await nextTick()

    // Create mask for fill effect
    const mask = document.createElement('div')
    mask.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: var(--color-background);
      z-index: 1;
    `

    element.style.position = 'relative'
    element.appendChild(mask)

    timeline = gsap.timeline({
      paused: !config.autoplay,
      delay: config.delay / 1000,
      repeat: config.loop ? -1 : 0,
      onComplete: () => {
        mask.remove()
        isAnimating.value = false
      },
    })

    // Animate mask based on fill direction
    const maskAnimation = getLatexMaskAnimation(mask, config.fillDirection)
    timeline.to(mask, {
      ...maskAnimation,
      duration: config.speed,
      ease: config.easing,
    })

    if (config.autoplay) {
      timeline.play()
    }
  }

  const getLatexMaskAnimation = (mask: HTMLElement, direction: string) => {
    switch (direction) {
      case 'top-to-bottom':
        return { y: '100%' }
      case 'center-out':
        gsap.set(mask, { transformOrigin: 'center center', scaleX: 1, scaleY: 1 })
        return { scaleX: 0, scaleY: 0 }
      case 'left-to-right':
      default:
        return { x: '100%' }
    }
  }

  const play = () => timeline?.play()
  const pause = () => timeline?.pause()
  const restart = () => {
    timeline?.restart()
    startAnimation()
  }

  const cleanup = () => {
    timeline?.kill()
    timeline = null
  }

  onMounted(() => {
    if (config.autoplay) {
      startAnimation()
    }
  })

  onUnmounted(cleanup)

  return {
    isAnimating,
    startAnimation,
    play,
    pause,
    restart,
    cleanup,
  }
}

// Master animation composable that provides all animation types
export function useTextAnimations() {
  return {
    useTypewriterAnimation,
    useHandwritingAnimation,
    useLatexFillAnimation,
  }
}