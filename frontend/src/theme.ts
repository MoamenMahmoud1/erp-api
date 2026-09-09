import { createTheme, rem } from '@mantine/core';

export const theme = createTheme({
  primaryColor: 'indigo',
  primaryShade: { light: 6, dark: 5 },
  defaultRadius: 'md',
  fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  headings: {
    fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif',
    fontWeight: '700',
  },
  defaultGradient: { from: 'indigo', to: 'cyan', deg: 120 },
  spacing: {
    xs: rem(8),
    sm: rem(12),
    md: rem(16),
    lg: rem(24),
    xl: rem(32),
  },
  shadows: {
    sm: '0 6px 20px rgba(0, 0, 0, 0.16)',
    md: '0 14px 45px rgba(0, 0, 0, 0.20)',
    lg: '0 24px 70px rgba(0, 0, 0, 0.28)',
  },
  focusClassName: 'erp-focus',
  cursorType: 'pointer',
});
