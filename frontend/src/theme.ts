import { createTheme, rem } from '@mantine/core';

const sapphire = [
  '#f2f5ff',
  '#e4e9ff',
  '#ccd5ff',
  '#aab8ff',
  '#8799ef',
  '#657ad6',
  '#4f63bd',
  '#414f99',
  '#36447d',
  '#2c3865',
] as const;

const emerald = [
  '#eef9f4',
  '#daf1e5',
  '#bce4cf',
  '#96d3b5',
  '#6fbe9a',
  '#4ca57d',
  '#388966',
  '#2f6e55',
  '#285945',
  '#214938',
] as const;

const amethyst = [
  '#f6f2fb',
  '#ebe2f7',
  '#dccbef',
  '#c7afe4',
  '#b18bd5',
  '#976bc4',
  '#7d53ad',
  '#674693',
  '#553a7b',
  '#463165',
] as const;

const amber = [
  '#fff8eb',
  '#ffedc7',
  '#ffdf9a',
  '#f6c96d',
  '#e4ad4e',
  '#c99135',
  '#aa772a',
  '#895f26',
  '#704f24',
  '#5d4321',
] as const;

export const theme = createTheme({
  colors: {
    erp: sapphire,
    blue: sapphire,
    cyan: sapphire,
    indigo: sapphire,
    teal: emerald,
    violet: amethyst,
    orange: amber,
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
