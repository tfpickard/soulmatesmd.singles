/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'rgb(var(--color-ink) / <alpha-value>)',
        paper: 'rgb(var(--color-paper) / <alpha-value>)',
        coral: 'rgb(var(--color-coral) / <alpha-value>)',
        mist: 'rgb(var(--color-mist) / <alpha-value>)',
      },
      boxShadow: {
        halo: '0 30px 90px rgb(var(--shadow-halo) / 0.28)',
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', 'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', 'serif'],
        body: ['"Space Grotesk"', '"Helvetica Neue"', 'Avenir Next', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
