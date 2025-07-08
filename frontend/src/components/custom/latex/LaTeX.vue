<template>
  <span 
    ref="mathElement" 
    :class="className"
    v-html="renderedMath"
  ></span>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import katex from 'katex';
import 'katex/dist/katex.min.css';

interface Props {
  expression: string;
  displayMode?: boolean;
  className?: string;
}

const props = withDefaults(defineProps<Props>(), {
  expression: '',
  displayMode: false,
  className: '',
});

const mathElement = ref<HTMLElement>();
const renderedMath = ref('');

const renderMath = () => {
  try {
    renderedMath.value = katex.renderToString(props.expression, {
      displayMode: props.displayMode,
      throwOnError: false,
      errorColor: '#cc0000',
      strict: false,
    });
  } catch (error) {
    console.error('KaTeX rendering error:', error);
    renderedMath.value = props.expression;
  }
};

onMounted(() => {
  renderMath();
});

watch(() => props.expression, () => {
  renderMath();
});
</script>

<style>
/* KaTeX global styles are imported above */
.katex {
  font-size: inherit;
}

.katex-display {
  margin: 0;
}
</style>