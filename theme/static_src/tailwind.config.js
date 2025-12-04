module.exports = {
  content: [
    // templates de l’app theme (base.html)
    '../templates/**/*.html',

    // templates globaux à la racine du projet
    '../../../templates/**/*.html',

    // templates des autres apps Django
    '../../../**/templates/**/*.html',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
