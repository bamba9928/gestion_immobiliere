/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // Templates Django
    './templates/**/*.html',
    './*/templates/**/*.html',  // Templates dans chaque app
    './apps/*/templates/**/*.html',  // Si structure apps/

    // Fichiers JavaScript
    './static/**/*.js',
    './*/static/**/*.js',
    './apps/*/static/**/*.js',

    // Fichiers Python avec classes CSS (rare mais utile)
    './**/*.py',
  ],

  theme: {
    extend: {
      colors: {
        // Palette MADA IMMO (extensible)
        primary: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',  // Emerald principal
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
          950: '#022c22',
        },
        // Alias pour cohérence
        emerald: {
          DEFAULT: '#10b981',
          light: '#6ee7b7',
          dark: '#047857',
        },
      },

      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },

      boxShadow: {
        'dark-lg': '0 10px 30px -5px rgba(0, 0, 0, 0.8)',
        'dark-xl': '0 20px 40px -10px rgba(0, 0, 0, 0.9)',
        'emerald-glow': '0 0 20px rgba(16, 185, 129, 0.3)',
      },

      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },

      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.4s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },

      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },

  plugins: [
    // Plugin pour formulaires Django
    require('@tailwindcss/forms')({
      strategy: 'class', // Utilise .form-input, .form-select, etc.
    }),

    // Plugin optionnel pour typographie
    // require('@tailwindcss/typography'),

    // Plugin custom pour composants Django
    function({ addComponents, theme }) {
      addComponents({
        // Boutons
        '.btn-primary': {
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: theme('spacing.2'),
          backgroundColor: theme('colors.emerald.500'),
          color: theme('colors.black'),
          fontSize: theme('fontSize.sm'),
          fontWeight: theme('fontWeight.semibold'),
          padding: `${theme('spacing.2.5')} ${theme('spacing.4')}`,
          borderRadius: theme('borderRadius.lg'),
          transition: 'all 150ms',
          '&:hover': {
            backgroundColor: theme('colors.emerald.400'),
          },
          '&:active': {
            backgroundColor: 'rgba(16, 185, 129, 0.9)',
          },
          '&:focus': {
            outline: 'none',
            ringWidth: '2px',
            ringColor: 'rgba(16, 185, 129, 0.7)',
            ringOffsetWidth: '2px',
            ringOffsetColor: theme('colors.neutral.950'),
          },
          '&:disabled': {
            opacity: '0.5',
            cursor: 'not-allowed',
          },
        },

        '.btn-secondary': {
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: theme('spacing.2'),
          backgroundColor: 'transparent',
          color: theme('colors.emerald.400'),
          fontSize: theme('fontSize.sm'),
          fontWeight: theme('fontWeight.semibold'),
          padding: `${theme('spacing.2.5')} ${theme('spacing.4')}`,
          borderRadius: theme('borderRadius.lg'),
          borderWidth: '1px',
          borderColor: theme('colors.emerald.500'),
          transition: 'all 150ms',
          '&:hover': {
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderColor: theme('colors.emerald.400'),
          },
          '&:focus': {
            outline: 'none',
            ringWidth: '2px',
            ringColor: 'rgba(16, 185, 129, 0.5)',
          },
        },

        '.btn-danger': {
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: theme('spacing.2'),
          backgroundColor: theme('colors.red.500'),
          color: theme('colors.white'),
          fontSize: theme('fontSize.sm'),
          fontWeight: theme('fontWeight.semibold'),
          padding: `${theme('spacing.2.5')} ${theme('spacing.4')}`,
          borderRadius: theme('borderRadius.lg'),
          transition: 'all 150ms',
          '&:hover': {
            backgroundColor: theme('colors.red.600'),
          },
        },

        // Cards
        '.card-dark': {
          backgroundColor: 'rgba(23, 23, 23, 0.9)',
          borderWidth: '1px',
          borderColor: theme('colors.neutral.800'),
          borderRadius: theme('borderRadius.2xl'),
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)',
          backdropFilter: 'blur(24px)',
        },

        '.card-hover': {
          transition: 'all 200ms',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 30px 60px -15px rgba(0, 0, 0, 0.7)',
            borderColor: theme('colors.neutral.700'),
          },
        },

        // Formulaires Django
        '.form-input-dark': {
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          borderWidth: '1px',
          borderColor: 'rgba(64, 64, 64, 0.8)',
          color: theme('colors.white'),
          fontSize: theme('fontSize.sm'),
          borderRadius: theme('borderRadius.lg'),
          padding: `${theme('spacing.2.5')} ${theme('spacing.3')}`,
          '&::placeholder': {
            color: theme('colors.neutral.500'),
          },
          '&:focus': {
            outline: 'none',
            borderColor: theme('colors.emerald.500'),
            ringWidth: '2px',
            ringColor: 'rgba(16, 185, 129, 0.7)',
          },
          '&:disabled': {
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            cursor: 'not-allowed',
          },
        },

        // Messages Django
        '.alert': {
          padding: theme('spacing.4'),
          borderRadius: theme('borderRadius.lg'),
          borderWidth: '1px',
          fontSize: theme('fontSize.sm'),
          fontWeight: theme('fontWeight.medium'),
        },

        '.alert-success': {
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          borderColor: theme('colors.emerald.500'),
          color: theme('colors.emerald.400'),
        },

        '.alert-error': {
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderColor: theme('colors.red.500'),
          color: theme('colors.red.400'),
        },

        '.alert-warning': {
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          borderColor: theme('colors.amber.500'),
          color: theme('colors.amber.400'),
        },

        '.alert-info': {
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderColor: theme('colors.blue.500'),
          color: theme('colors.blue.400'),
        },

        // Tables
        '.table-dark': {
          width: '100%',
          fontSize: theme('fontSize.sm'),
          '& thead': {
            borderBottomWidth: '1px',
            borderColor: theme('colors.neutral.700'),
          },
          '& th': {
            padding: `${theme('spacing.3')} ${theme('spacing.4')}`,
            textAlign: 'left',
            fontWeight: theme('fontWeight.semibold'),
            color: theme('colors.neutral.300'),
          },
          '& td': {
            padding: `${theme('spacing.3')} ${theme('spacing.4')}`,
            borderBottomWidth: '1px',
            borderColor: theme('colors.neutral.800'),
          },
          '& tbody tr:hover': {
            backgroundColor: 'rgba(23, 23, 23, 0.5)',
          },
        },

        // Badges
        '.badge': {
          display: 'inline-flex',
          alignItems: 'center',
          padding: `${theme('spacing.1')} ${theme('spacing.2')}`,
          fontSize: theme('fontSize.xs'),
          fontWeight: theme('fontWeight.semibold'),
          borderRadius: theme('borderRadius.md'),
        },

        '.badge-success': {
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          color: theme('colors.emerald.400'),
        },

        '.badge-danger': {
          backgroundColor: 'rgba(239, 68, 68, 0.2)',
          color: theme('colors.red.400'),
        },

        '.badge-warning': {
          backgroundColor: 'rgba(245, 158, 11, 0.2)',
          color: theme('colors.amber.400'),
        },
      });
    },
  ],

}