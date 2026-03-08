/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        zone: {
          1: '#3B82F6',
          2: '#22C55E',
          3: '#EAB308',
          4: '#F97316',
          5: '#EF4444',
        },
      },
    },
  },
}
