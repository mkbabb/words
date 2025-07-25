import { ref, onMounted, onUnmounted, nextTick, type Ref } from 'vue'
import { gsap } from 'gsap'

export interface ThreeB1BAnimationOptions {
  speed?: number
  delay?: number
  autoplay?: boolean
  loop?: boolean
  easing?: string
  fillStyle?: '3b1b-radial' | '3b1b-diamond' | '3b1b-morph' | '3b1b-sweep' | '3b1b-write' | 'radial-pulse' | 'equation-reveal'
  colorHighlights?: boolean
  stagger?: number
}

/**
 * 3Blue1Brown-style animation composable
 * Provides various mathematical/educational animation styles inspired by 3b1b's manim library
 */
export function use3b1bAnimation(
  elementRef: Ref<HTMLElement | null>,
  options: ThreeB1BAnimationOptions = {}
) {
  const isAnimating = ref(false)
  let timeline: gsap.core.Timeline | null = null

  const defaultOptions: Required<ThreeB1BAnimationOptions> = {
    speed: 1.5,
    delay: 0,
    autoplay: true,
    loop: false,
    easing: 'power3.inOut',
    fillStyle: '3b1b-radial',
    colorHighlights: false,
    stagger: 0.05,
  }

  const config = { ...defaultOptions, ...options }

  const startAnimation = async () => {
    if (!elementRef.value || isAnimating.value) return

    isAnimating.value = true
    await nextTick()

    const element = elementRef.value

    // Create timeline
    timeline = gsap.timeline({
      paused: !config.autoplay,
      delay: config.delay / 1000,
      repeat: config.loop ? -1 : 0,
      onComplete: () => {
        isAnimating.value = false
      },
    })

    switch (config.fillStyle) {
      case '3b1b-radial':
        animate3b1bRadial(timeline, element)
        break
      case '3b1b-diamond':
        animate3b1bDiamond(timeline, element)
        break
      case '3b1b-morph':
        animate3b1bMorph(timeline, element)
        break
      case '3b1b-sweep':
        animate3b1bSweep(timeline, element)
        break
      case '3b1b-write':
        animate3b1bWrite(timeline, element)
        break
      case 'radial-pulse':
        animateRadialPulse(timeline, element)
        break
      case 'equation-reveal':
        animateEquationReveal(timeline, element)
        break
    }

    if (config.autoplay) {
      timeline.play()
    }
  }

  // 3b1b-style radial reveal (expanding circle)
  const animate3b1bRadial = (tl: gsap.core.Timeline, element: HTMLElement) => {
    tl.fromTo(element, 
      {
        clipPath: 'circle(0% at 50% 50%)',
        opacity: 0.8,
        scale: 0.9,
      },
      {
        clipPath: 'circle(150% at 50% 50%)',
        opacity: 1,
        scale: 1,
        duration: config.speed,
        ease: config.easing,
      }
    )
  }

  // Diamond/polygon reveal
  const animate3b1bDiamond = (tl: gsap.core.Timeline, element: HTMLElement) => {
    tl.fromTo(element,
      {
        clipPath: 'polygon(50% 50%, 50% 50%, 50% 50%, 50% 50%)',
        opacity: 0.8,
      },
      {
        clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
        opacity: 1,
        duration: config.speed,
        ease: 'back.out(1.7)',
      }
    )
  }

  // Morphing ellipse reveal
  const animate3b1bMorph = (tl: gsap.core.Timeline, element: HTMLElement) => {
    tl.fromTo(element,
      {
        clipPath: 'ellipse(0% 0% at 50% 50%)',
        filter: 'blur(4px)',
        opacity: 0.7,
      },
      {
        clipPath: 'ellipse(100% 100% at 50% 50%)',
        filter: 'blur(0px)',
        opacity: 1,
        duration: config.speed,
        ease: config.easing,
      }
    )
  }

  // Multi-directional sweep
  const animate3b1bSweep = (tl: gsap.core.Timeline, element: HTMLElement) => {
    // Create a complex polygon animation
    tl.fromTo(element,
      {
        clipPath: 'polygon(50% 50%, 50% 50%, 50% 50%, 50% 50%, 50% 50%, 50% 50%, 50% 50%, 50% 50%)',
        opacity: 0.8,
      },
      {
        clipPath: 'polygon(0% 0%, 50% 0%, 100% 0%, 100% 50%, 100% 100%, 50% 100%, 0% 100%, 0% 50%)',
        opacity: 1,
        duration: config.speed,
        ease: 'power4.out',
      }
    )
  }

  // Write-on effect (requires special setup)
  const animate3b1bWrite = (tl: gsap.core.Timeline, element: HTMLElement) => {
    // Create overlay element for write-on effect
    const overlay = document.createElement('div')
    overlay.style.position = 'absolute'
    overlay.style.top = '0'
    overlay.style.left = '0'
    overlay.style.right = '0'
    overlay.style.bottom = '0'
    overlay.style.background = 'inherit'
    overlay.style.pointerEvents = 'none'
    
    if (element.parentElement) {
      element.parentElement.style.position = 'relative'
      element.parentElement.appendChild(overlay)
    }

    tl.fromTo(overlay,
      {
        clipPath: 'inset(0 0 0 100%)',
      },
      {
        clipPath: 'inset(0 0 0 0%)',
        duration: config.speed,
        ease: 'power2.inOut',
        onComplete: () => {
          overlay.remove()
        }
      }
    )
  }

  // Radial pulse (growing rings)
  const animateRadialPulse = (tl: gsap.core.Timeline, element: HTMLElement) => {
    tl.fromTo(element,
      {
        clipPath: 'circle(0% at 50% 50%)',
        scale: 0.8,
        opacity: 0,
      },
      {
        clipPath: 'circle(100% at 50% 50%)',
        scale: 1,
        opacity: 1,
        duration: config.speed * 0.6,
        ease: 'power2.out',
      }
    )
    .to(element, {
      scale: 1.05,
      duration: config.speed * 0.2,
      ease: 'power2.in',
    })
    .to(element, {
      scale: 1,
      duration: config.speed * 0.2,
      ease: 'power2.out',
    })
  }

  // Equation-style reveal (for mathematical content)
  const animateEquationReveal = (tl: gsap.core.Timeline, element: HTMLElement) => {
    // If element contains multiple children (terms), animate them separately
    const children = element.children
    
    if (children.length > 0 && config.stagger) {
      // Animate each child with stagger
      gsap.set(children, { opacity: 0, scale: 0.7, y: 10 })
      
      tl.to(children, {
        opacity: 1,
        scale: 1,
        y: 0,
        duration: config.speed / children.length,
        stagger: config.stagger,
        ease: 'back.out(1.4)',
      })
    } else {
      // Single element animation
      tl.fromTo(element,
        {
          clipPath: 'inset(0 100% 0 0)',
          opacity: 0.7,
        },
        {
          clipPath: 'inset(0 0% 0 0)',
          opacity: 1,
          duration: config.speed,
          ease: 'power3.out',
        }
      )
    }

    // Add color highlights if enabled
    if (config.colorHighlights) {
      addColorHighlights(tl, element)
    }
  }

  // Add 3b1b-style color highlights
  const addColorHighlights = (tl: gsap.core.Timeline, element: HTMLElement) => {
    const highlights = element.querySelectorAll('.highlight')
    if (highlights.length > 0) {
      tl.fromTo(highlights,
        {
          backgroundColor: 'transparent',
          padding: '0',
        },
        {
          backgroundColor: 'rgba(59, 130, 246, 0.2)',
          padding: '0 0.2em',
          duration: 0.3,
          stagger: 0.1,
          ease: 'power2.out',
        },
        '-=0.5'
      )
    }
  }

  const play = () => timeline?.play()
  const pause = () => timeline?.pause()
  const restart = () => {
    timeline?.kill()
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

/**
 * SVG Path Animation for 3b1b-style drawing effects
 */
export function use3b1bPathAnimation(
  pathRef: Ref<SVGPathElement | null>,
  options: Partial<ThreeB1BAnimationOptions> = {}
) {
  const isAnimating = ref(false)
  let timeline: gsap.core.Timeline | null = null

  const config = {
    speed: 2,
    delay: 0,
    autoplay: true,
    loop: false,
    easing: 'none',
    strokeWidth: 3,
    strokeColor: '#3b82f6',
    ...options,
  }

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
      stroke: config.strokeColor,
      fill: 'none',
      opacity: 0,
    })

    timeline = gsap.timeline({
      paused: !config.autoplay,
      delay: config.delay / 1000,
      repeat: config.loop ? -1 : 0,
      onComplete: () => {
        isAnimating.value = false
      },
    })

    // Fade in
    timeline.to(path, {
      opacity: 1,
      duration: 0.2,
      ease: 'power2.out',
    })

    // Draw path with variable speed
    timeline.to(path, {
      strokeDashoffset: 0,
      duration: config.speed,
      ease: config.easing,
    })

    // Optional fill animation at the end
    timeline.to(path, {
      fill: config.strokeColor,
      fillOpacity: 0.1,
      duration: 0.3,
      ease: 'power2.out',
    }, '-=0.2')

    if (config.autoplay) {
      timeline.play()
    }
  }

  const play = () => timeline?.play()
  const pause = () => timeline?.pause()
  const restart = () => {
    timeline?.kill()
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