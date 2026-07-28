/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#ecfeff',
          100: '#cffaff',
          200: '#a5f3fc',
          300: '#67e8f9',
          400: '#22d3ee',
          500: '#06b6d4',
          600: '#0891b2',
          700: '#0e7490',
          800: '#155e75',
          900: '#164e63',
          glow: '#00f2fe',
        },
        dark: {
          bg: '#0b0f17',
          card: '#131924',
          border: '#1e293b',
          hover: '#1e293b',
        }
      },
      boxShadow: {
        'glow-cyan': '0 0 20px -3px rgba(6, 182, 212, 0.4)',
        'glow-violet': '0 0 20px -3px rgba(139, 92, 246, 0.4)',
      }
    },
  },
  plugins: [],
}
