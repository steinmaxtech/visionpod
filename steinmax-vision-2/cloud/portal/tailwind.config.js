/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme - industrial/security aesthetic
        'void': '#0a0a0b',
        'surface': {
          DEFAULT: '#111113',
          raised: '#18181b',
          overlay: '#1f1f23',
        },
        'border': {
          DEFAULT: '#27272a',
          subtle: '#1f1f23',
          strong: '#3f3f46',
        },
        'text': {
          primary: '#fafafa',
          secondary: '#a1a1aa',
          muted: '#71717a',
        },
        'accent': {
          DEFAULT: '#10b981',
          hover: '#34d399',
          muted: '#065f46',
        },
        'status': {
          granted: '#10b981',
          denied: '#ef4444',
          unknown: '#f59e0b',
          online: '#10b981',
          offline: '#6b7280',
        }
      },
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
