/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        trading: {
          bg: '#0f172a', // Slate 900
          panel: '#1e293b', // Slate 800
          border: '#334155', // Slate 700
          text: '#f8fafc',
          muted: '#94a3b8',
          buy: '#10b981', // Emerald 500
          sell: '#ef4444', // Red 500
          buyBg: 'rgba(16, 185, 129, 0.15)',
          sellBg: 'rgba(239, 68, 68, 0.15)',
          wall: '#f59e0b', // Amber 500
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
