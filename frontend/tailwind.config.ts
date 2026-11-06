import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0d1117',
        panel: '#131a24',
        raised: '#1a2332',
        line: '#252f3d',
        ink: '#d7dee8',
        dim: '#7c8a9c',
        accent: '#ecad0a',
        blue: '#209dd7',
        purple: '#753991',
        up: '#2ecc8f',
        down: '#ff5c6a',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SF Mono', 'Menlo', 'Consolas', 'monospace'],
        sans: ['ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
export default config;
