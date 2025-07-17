export { default as DarkModeToggle } from './DarkModeToggle.vue';

import { useDark, useToggle } from '@vueuse/core';

const isDark = useDark({ disableTransition: false });
const toggleDark = useToggle(isDark);

export const changeTheme = () => {
  toggleDark();
};

export { isDark };
