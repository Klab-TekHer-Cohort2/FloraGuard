/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        heading: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        'plus-jakarta-sans': ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        inter: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#1F6F4A',
          hover: '#185A3C',
          tint: '#E6F2EC',
        },
        accent: {
          DEFAULT: '#C2185B',
          hover: '#A3144C',
          tint: '#FCE7F0',
        },
        'risk-low': {
          DEFAULT: '#2E7D32',
          tint: '#E8F5E9',
        },
        'risk-medium': {
          DEFAULT: '#E08A00',
          tint: '#FFF8E1',
        },
        'risk-high': {
          DEFAULT: '#C62828',
          tint: '#FFEBEE',
        },
        surface: '#FFFFFF',
        'border-default': '#E7E2DB',
        'text-primary': '#1F2933',
        'text-muted': '#5B6770',
        bg: '#FAF8F5',
      },
      borderRadius: {
        card: '16px',
        btn: '12px',
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
      },
      maxWidth: {
        content: '1200px',
      },
      boxShadow: {
        card: '0 2px 12px 0 rgba(31,47,51,0.07)',
        'card-hover': '0 4px 24px 0 rgba(31,47,51,0.12)',
      },
    },
  },
  plugins: [],
};
