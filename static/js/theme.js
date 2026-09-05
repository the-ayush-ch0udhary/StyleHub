/**
 * StyleHub — Light/Dark Theme Switcher
 * Persists theme preference across page reloads using localStorage.
 */
(function () {
  'use strict';

  const THEME_STORAGE_KEY = 'stylehub_theme';

  function getStoredTheme() {
    return localStorage.getItem(THEME_STORAGE_KEY);
  }

  function getPreferredTheme() {
    const stored = getStoredTheme();
    if (stored) {
      return stored;
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    updateThemeToggleUI(theme);
  }

  function updateThemeToggleUI(theme) {
    const toggleBtns = document.querySelectorAll('.theme-toggle-btn');
    toggleBtns.forEach(btn => {
      const icon = btn.querySelector('i');
      if (icon) {
        if (theme === 'dark') {
          icon.className = 'bi bi-sun-fill text-warning';
          btn.setAttribute('title', 'Switch to Light Theme');
        } else {
          icon.className = 'bi bi-moon-stars-fill';
          btn.setAttribute('title', 'Switch to Dark Theme');
        }
      }
    });
  }

  // Set theme immediately on load
  const initialTheme = getPreferredTheme();
  setTheme(initialTheme);

  window.addEventListener('DOMContentLoaded', () => {
    updateThemeToggleUI(getPreferredTheme());

    document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(nextTheme);
      });
    });
  });
})();
