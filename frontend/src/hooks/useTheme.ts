// Custom hook for theme management

import { useEffect, useCallback, useState } from 'react';
import { useAppStore } from '../store';
import { useLocalStorage } from './useLocalStorage';
import { STORAGE_KEYS } from '../utils/constants';
import type { Theme } from '../types';

export interface UseThemeReturn {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  isDark: boolean;
  isLight: boolean;
  isAuto: boolean;
  systemTheme: Theme;
}

/**
 * Custom hook for managing application theme
 * @returns Theme state and actions
 */
export function useTheme(): UseThemeReturn {
  const { theme, setTheme: setStoreTheme, toggleTheme: toggleStoreTheme } = useAppStore();
  const [storedTheme, setStoredTheme] = useLocalStorage<Theme>(STORAGE_KEYS.THEME, 'auto');

  // Get system theme preference
  const getSystemTheme = useCallback((): Theme => {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }, []);

  // Resolve actual theme (convert 'auto' to 'light' or 'dark')
  const resolveTheme = useCallback((themeValue: Theme): Theme => {
    if (themeValue === 'auto') {
      return getSystemTheme();
    }
    return themeValue;
  }, [getSystemTheme]);

  // Apply theme to document
  const applyTheme = useCallback((themeValue: Theme) => {
    if (typeof window === 'undefined') return;

    const resolvedTheme = resolveTheme(themeValue);
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light', 'dark');
    
    // Add new theme class
    root.classList.add(resolvedTheme);
    
    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      const color = resolvedTheme === 'dark' ? '#1a1a1a' : '#ffffff';
      metaThemeColor.setAttribute('content', color);
    }
    
    // Update color-scheme for better browser integration
    root.style.colorScheme = resolvedTheme;
  }, [resolveTheme]);

  // Set theme
  const setTheme = useCallback((newTheme: Theme) => {
    setStoreTheme(newTheme);
    setStoredTheme(newTheme);
    applyTheme(newTheme);
  }, [setStoreTheme, setStoredTheme, applyTheme]);

  // Toggle theme
  const toggleTheme = useCallback(() => {
    const currentResolved = resolveTheme(theme);
    const newTheme: Theme = currentResolved === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  }, [theme, resolveTheme, setTheme]);

  // Initialize theme from localStorage
  useEffect(() => {
    if (storedTheme !== theme) {
      setStoreTheme(storedTheme);
    }
    applyTheme(storedTheme);
  }, [storedTheme, theme, setStoreTheme, applyTheme]);

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = () => {
      if (theme === 'auto') {
        applyTheme('auto');
      }
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
    // Legacy browsers
    else if (mediaQuery.addListener) {
      mediaQuery.addListener(handleChange);
      return () => mediaQuery.removeListener(handleChange);
    }
  }, [theme, applyTheme]);

  // Handle visibility change to sync theme
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleVisibilityChange = () => {
      if (!document.hidden && theme === 'auto') {
        applyTheme('auto');
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [theme, applyTheme]);

  const systemTheme = getSystemTheme();
  const resolvedTheme = resolveTheme(theme);

  return {
    theme,
    setTheme,
    toggleTheme,
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
    isAuto: theme === 'auto',
    systemTheme,
  };
}

/**
 * Custom hook for getting theme-aware CSS classes
 * @param lightClass - CSS class for light theme
 * @param darkClass - CSS class for dark theme
 * @returns Current theme-appropriate CSS class
 */
export function useThemeClass(lightClass: string, darkClass: string): string {
  const { isDark } = useTheme();
  return isDark ? darkClass : lightClass;
}

/**
 * Custom hook for getting theme-aware values
 * @param lightValue - Value for light theme
 * @param darkValue - Value for dark theme
 * @returns Current theme-appropriate value
 */
export function useThemeValue<T>(lightValue: T, darkValue: T): T {
  const { isDark } = useTheme();
  return isDark ? darkValue : lightValue;
}

/**
 * Custom hook for detecting system theme preference
 * @returns System theme preference
 */
export function useSystemTheme(): Theme {
  const [systemTheme, setSystemTheme] = useState<Theme>('light');

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const updateSystemTheme = () => {
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setSystemTheme(isDark ? 'dark' : 'light');
    };

    // Initial check
    updateSystemTheme();

    // Listen for changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', updateSystemTheme);
      return () => mediaQuery.removeEventListener('change', updateSystemTheme);
    } else if (mediaQuery.addListener) {
      mediaQuery.addListener(updateSystemTheme);
      return () => mediaQuery.removeListener(updateSystemTheme);
    }
  }, []);

  return systemTheme;
}