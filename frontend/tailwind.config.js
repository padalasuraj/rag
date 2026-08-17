/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Deep-space navy base (dark-first) — intentionally not pure black.
        bg: { DEFAULT: '#070B14', soft: '#0A1120', panel: '#0E1626' },
        ink: { DEFAULT: '#E6EDF6', muted: '#8A93A6', dim: '#5A6478' },
        // Signature accent from the brief (cyan) + a premium violet partner.
        accent: '#00DBDE',
        violet: '#7C5CFF',
        success: '#34D399',
        warn: '#FBBF24',
        danger: '#F87171',
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 40px -8px rgba(0, 219, 222, 0.45)',
        'glow-violet': '0 0 40px -8px rgba(124, 92, 255, 0.45)',
        card: '0 20px 60px -30px rgba(0, 0, 0, 0.8)',
      },
      backgroundImage: {
        'grad-accent': 'linear-gradient(135deg, #00DBDE 0%, #7C5CFF 100%)',
        'grad-accent-soft':
          'linear-gradient(135deg, rgba(0,219,222,0.15) 0%, rgba(124,92,255,0.15) 100%)',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-ring': {
          '0%': { transform: 'scale(0.9)', opacity: '0.7' },
          '80%, 100%': { transform: 'scale(1.6)', opacity: '0' },
        },
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        float: 'float 6s ease-in-out infinite',
        'pulse-ring': 'pulse-ring 3s ease-out infinite',
      },
    },
  },
  plugins: [],
}
