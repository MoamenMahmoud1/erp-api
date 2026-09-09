import { createTheme, rem } from '@mantine/core';

export const theme = createTheme({
  colors: {
    erp: [
      '#eef5f8',
      '#d9e8ee',
      '#bfd9e2',
      '#9fc3d1',
      '#7fa9bb',
      '#5f8fa5',
      '#46778f',
      '#356177',
      '#294e61',
      '#1e3b49',
    ],
  },
  primaryColor: 'erp',
  primaryShade: { light: 6, dark: 5 },
  defaultRadius: 'sm',
  fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  headings: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    fontWeight: '700',
  },
  spacing: {
    xs: rem(6),
    sm: rem(10),
    md: rem(14),
    lg: rem(20),
    xl: rem(28),
  },
  shadows: {
    xs: '0 1px 2px rgba(15, 23, 42, 0.04)',
    sm: '0 3px 10px rgba(15, 23, 42, 0.06)',
    md: '0 8px 20px rgba(15, 23, 42, 0.08)',
  },
  focusClassName: 'erp-focus',
  cursorType: 'pointer',
});
