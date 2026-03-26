/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0c1117',
        paper: '#f4efe8',
        coral: '#ff7c64',
        mist: '#9aa6b2',
      },
      boxShadow: {
        halo: '0 30px 80px rgba(255, 124, 100, 0.12)',
      },
      fontFamily: {
        display: ['Georgia', 'serif'],
        body: ['ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
