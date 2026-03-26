import { cva, type VariantProps } from 'class-variance-authority'

export { default as Button } from './Button.vue'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-colors duration-150 focus-ring active:scale-95 disabled-base data-[disabled]:pointer-events-none data-[disabled]:opacity-50 data-[state=on]:shadow-card [&_svg]:pointer-events-none [&_svg:not([class*=\'size-\'])]:size-4 shrink-0 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground shadow-subtle hover:bg-primary/90 data-[state=on]:bg-primary/90',
        destructive:
          'bg-destructive text-destructive-foreground shadow-subtle hover:bg-destructive/90 data-[state=on]:bg-destructive/90',
        outline:
          'border border-input bg-background shadow-subtle hover:border-border/80 hover:bg-accent hover:text-accent-foreground data-[state=on]:border-primary/35 data-[state=on]:bg-primary/10 data-[state=on]:text-primary',
        secondary:
          'bg-secondary text-secondary-foreground shadow-subtle hover:bg-secondary/80 data-[state=on]:bg-secondary/80',
        ghost:
          'bg-muted/40 hover:bg-accent hover:text-accent-foreground data-[state=on]:bg-accent data-[state=on]:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline hover:text-primary/80',
        glass:
          'glass-medium text-foreground shadow-subtle hover:border-border/60 hover:bg-background/95 data-[state=on]:border-primary/30 data-[state=on]:bg-primary/10 data-[state=on]:text-primary',
        'glass-subtle':
          'glass-light text-foreground/70 shadow-subtle hover:border-border/50 hover:text-foreground data-[state=on]:border-primary/25 data-[state=on]:bg-primary/5 data-[state=on]:text-primary',
        'glass-flat':
          'bg-card border border-border/30 text-foreground/70 shadow-subtle hover:border-border/50 hover:text-foreground data-[state=on]:border-primary/25 data-[state=on]:bg-primary/5 data-[state=on]:text-primary',
        ai:
          'border border-amber-500/30 bg-amber-100/80 text-amber-900 shadow-subtle hover:bg-amber-200/85 dark:border-amber-700/40 dark:bg-amber-950/40 dark:text-amber-200 dark:hover:bg-amber-900/55 data-[state=on]:border-amber-500/45 data-[state=on]:bg-amber-200/90 data-[state=on]:dark:bg-amber-900/70',
        'danger-subtle':
          'border border-destructive/25 bg-destructive/10 text-destructive shadow-subtle hover:bg-destructive/15 hover:border-destructive/35 data-[state=on]:border-destructive/40 data-[state=on]:bg-destructive/20',
      },
      size: {
        default: 'h-9 px-4 py-2 has-[>svg]:px-3',
        sm: 'h-8 rounded-lg gap-1.5 px-3 has-[>svg]:px-2.5',
        lg: 'h-10 rounded-xl px-6 has-[>svg]:px-4',
        icon: 'size-9 rounded-full',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
