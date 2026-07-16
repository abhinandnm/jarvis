/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          blue: "#00f0ff",
          dark: "#0a192f",
          darker: "#020c1b",
          light: "#00f0ff",
          glow: "#005b82",
          gray: "#8892b0",
        }
      },
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        inter: ['Inter', 'sans-serif'],
        mono: ['Share Tech Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 8s linear infinite',
        'spin-reverse': 'spin-reverse 12s linear infinite',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'spin-reverse': {
          to: { transform: 'rotate(-360deg)' },
        },
        'glow-pulse': {
          '0%, 100%': {
            boxShadow: '0 0 15px rgba(0, 240, 255, 0.3), inset 0 0 15px rgba(0, 240, 255, 0.3)',
            borderColor: 'rgba(0, 240, 255, 0.6)'
          },
          '50%': {
            boxShadow: '0 0 30px rgba(0, 240, 255, 0.7), inset 0 0 25px rgba(0, 240, 255, 0.5)',
            borderColor: 'rgba(0, 240, 255, 1)'
          }
        }
      }
    },
  },
  plugins: [],
}
