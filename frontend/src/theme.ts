import { createTheme, rem } from '@mantine/core';

const erpBlue = [
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
] as const;

const erpTeal = [
  '#edf7f4',
  '#d9ebe5',
  '#bfddd2',
  '#a1cdbd',
  '#82bca6',
  '#66a88f',
  '#4d9479',
  '#3f7d67',
  '#356855',
  '#2b5244',
] as const;

const erpAmber = [
  '#fbf4e8',
  '#f5e6cd',
  '#edd6ad',
  '#e3c08b',
  '#d7a96b',
  '#ca9650',
  '#b9813f',
  '#9e6c35',
  '#83572d',
  '#684724',
] as const;

export const theme = createTheme({
  colors: {
    erp: erpBlue,
    blue: erpBlue,
    cyan: erpBlue,
    indigo: erpBlue,
    violet: erpTeal,
    teal: erpTeal,
    orange: erpAmber,
  },
  primaryColor: 'erp',
  primaryShade: { light: 6, dark: 5 },
  defaultRadius: 'sm',
  fontFamily:
    'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
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
