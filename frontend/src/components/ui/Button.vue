<template>
  <button
    :class="cn(buttonVariants({ variant, size }), className)"
    :disabled="disabled"
    v-bind="$attrs"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/utils';

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center',
    'rounded-xl text-sm font-medium whitespace-nowrap',
    'hover-lift focus-ring',
    'active:scale-95 disabled:pointer-events-none disabled:opacity-50',
  ].join(' '),
  {
    variants: {
      variant: {
        default:
          'bg-primary text-primary-foreground shadow-subtle',
        destructive:
          'bg-destructive text-destructive-foreground shadow-subtle',
        outline:
          'border border-input bg-background hover:bg-accent hover:text-accent-foreground shadow-subtle',
        secondary:
          'bg-secondary text-secondary-foreground shadow-subtle',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline hover-text-grow',
      },
      size: {
        default: 'h-9 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-10 px-8 text-base',
        icon: 'h-9 w-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface ButtonProps {
  variant?: VariantProps<typeof buttonVariants>['variant'];
  size?: VariantProps<typeof buttonVariants>['size'];
  disabled?: boolean;
  className?: string;
}

const props = withDefaults(defineProps<ButtonProps>(), {
  variant: 'default',
  size: 'default',
  disabled: false,
});

const { variant, size, disabled, className } = props;
</script>
