module.exports = {
  content: [
    // main templates directory
    '../../templates/**/*.html',

    // templates inside each app
    '../../**/templates/**/*.html',

    // if you use Tailwind classes in JS/TS files
    '../../**/*.js',
    '../../**/*.jsx',
    '../../**/*.ts',
    '../../**/*.tsx',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
