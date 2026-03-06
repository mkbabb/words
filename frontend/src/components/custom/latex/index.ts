import { defineAsyncComponent, h } from 'vue';

export const LaTeX = defineAsyncComponent({
  loader: () => import('./LaTeX.vue'),
  loadingComponent: {
    props: ['expression'],
    setup(props: { expression?: string }) {
      const text = props.expression
        ?.replace(/\\(?:mathfrak|mathcal|text)\{([^}]*)\}/g, '$1')
        .replace(/[\\{}_^]/g, '') || '';
      return () => h('span', text);
    },
  },
});
