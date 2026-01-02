import { useState, useEffect, useCallback } from 'react';

export type Theme = 'dark' | 'light';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    // Check localStorage first
    const stored = localStorage.getItem('photo-score-theme');
    if (stored === 'light' || stored === 'dark') {
      return stored;
    }
    // Default to dark theme (matches our design)
    return 'dark';
  });

  useEffect(() => {
    // Save to localStorage
    localStorage.setItem('photo-score-theme', theme);

    // Apply theme class to document
    if (theme === 'light') {
      document.documentElement.classList.add('light-theme');
    } else {
      document.documentElement.classList.remove('light-theme');
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, setTheme, toggleTheme };
}
