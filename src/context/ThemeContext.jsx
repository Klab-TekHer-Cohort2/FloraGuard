/**
 * ThemeContext — provides { theme, toggleTheme } to the whole app.
 *
 * - Reads from localStorage key "fg_theme" on mount.
 * - Falls back to the user's OS preference (prefers-color-scheme).
 * - Sets `data-theme` on `document.documentElement` whenever theme changes.
 */

import { createContext, useContext, useEffect, useState } from 'react';

const STORAGE_KEY = 'fg_theme';

const ThemeContext = createContext({
  theme: 'light',
  toggleTheme: () => {},
});

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark') return stored;
    } catch {
      // localStorage unavailable
    }
    // Fall back to OS preference
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  });

  // Apply data-theme attribute whenever theme changes
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // localStorage unavailable
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

/** Convenience hook */
export function useTheme() {
  return useContext(ThemeContext);
}
