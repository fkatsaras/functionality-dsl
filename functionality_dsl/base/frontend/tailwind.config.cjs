/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{svelte,ts}', './src/routes/**/*.{svelte,ts}'],
  theme: {
    extend: {
      colors: {
        dag: {
          canvas: '#0E1116',
          surface: '#0F172A',
          card: '#0B1220',
          edge: '#2B3445',
          edgeSoft: '#1F2837',
          text: '#E5E7EB',
          textMuted: '#A7B0C0',
          accent: '#7C83FF',
          accentSoft: '#9BA1FF',
          success: '#22C55E',
          warn: '#F59E0B',
          danger: '#EF4444'
        }
      },
      fontFamily: {
        approachmono: [
          '"Approach Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo',
          'Monaco', 'Consolas', '"Liberation Mono"', '"Courier New"', 'monospace'
        ]
      },
      borderRadius: { xl2: '1rem' },
      boxShadow: { card: '0 1px 0 rgba(255,255,255,0.03), 0 8px 24px rgba(0,0,0,0.35)' }
    }
  },
  plugins: []
};
