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
    speed: 100, // milliseconds between characters (slower = higher number)
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
    const charDuration = config.speed / 1000 // Convert milliseconds to seconds for GSAP

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

    // Use CSS clip-path for clean fill effect
    const initialClipPath = getInitialClipPath(config.fillDirection)
    const finalClipPath = getFinalClipPath(config.fillDirection)

    // Set initial state based on fill direction
    const initialState = get3b1bInitialState(config.fillDirection)
    const finalState = get3b1bFinalState(config.fillDirection)

    gsap.set(element, {
      clipPath: initialClipPath,
      ...initialState
    })

    timeline = gsap.timeline({
      paused: !config.autoplay,
      delay: config.delay / 1000,
      repeat: config.loop ? -1 : 0,
      onComplete: () => {
        gsap.set(element, { clipPath: 'none' })
        isAnimating.value = false
      },
    })

    timeline.to(element, {
      clipPath: finalClipPath,
      ...finalState,
      duration: config.speed,
      ease: config.easing,
    })

    if (config.autoplay) {
      timeline.play()
    }
  }

  const get3b1bInitialState = (direction: string) => {
    switch (direction) {
      case '3b1b-radial':
      case '3b1b-diamond':
        return { scale: 0.9, opacity: 0.8 }
      case '3b1b-morph':
        return { scale: 0.8, opacity: 0.7, filter: 'blur(4px)' }
      default:
        return {}
    }
  }

  const get3b1bFinalState = (direction: string) => {
    switch (direction) {
      case '3b1b-radial':
      case '3b1b-diamond':
        return { scale: 1, opacity: 1 }
      case '3b1b-morph':
        return { scale: 1, opacity: 1, filter: 'blur(0px)' }
      default:
        return {}
    }
  }

  const getInitialClipPath = (direction: string) => {
    switch (direction) {
      case 'top-to-bottom':
        return 'inset(0 0 100% 0)'
      case 'center-out':
        return 'inset(50% 50% 50% 50%)'
      case '3b1b-radial':
        return 'circle(0% at 50% 50%)'
      case '3b1b-diamond':
        return 'polygon(50% 50%, 50% 50%, 50% 50%, 50% 50%)'
      case '3b1b-morph':
        return 'ellipse(0% 0% at 50% 50%)'
      case 'left-to-right':
      default:
        return 'inset(0 100% 0 0)'
    }
  }

  const getFinalClipPath = (direction: string) => {
    switch (direction) {
      case 'top-to-bottom':
        return 'inset(0 0 0% 0)'
      case 'center-out':
        return 'inset(0% 0% 0% 0%)'
      case '3b1b-radial':
        return 'circle(150% at 50% 50%)'
      case '3b1b-diamond':
        return 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)'
      case '3b1b-morph':
        return 'ellipse(100% 100% at 50% 50%)'
      case 'left-to-right':
      default:
        return 'inset(0 0% 0 0)'
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