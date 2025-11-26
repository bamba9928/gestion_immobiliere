/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/*.html',
    './apps/**/*.py', // Pour scanner les classes dans les forms.py si besoin
  ],
  darkMode: 'class', // CRITIQUE pour le projet
  theme: {
    extend: {},
  },
  plugins: [],
}