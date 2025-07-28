// Custom hook for keyboard shortcuts and key handling

import { useEffect, useCallback, useRef, useState } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  meta?: boolean;
  preventDefault?: boolean;
  stopPropagation?: boolean;
}

export interface UseKeyboardOptions {
  target?: HTMLElement | Document | Window | null;
  enabled?: boolean;
}

/**
 * Custom hook for handling keyboard shortcuts
 * @param shortcuts - Object mapping shortcut combinations to callback functions
 * @param options - Configuration options
 */
export function useKeyboard(
  shortcuts: Record<string, (event: KeyboardEvent) => void>,
  options: UseKeyboardOptions = {}
): void {
  const { target = document, enabled = true } = options;
  const shortcutsRef = useRef(shortcuts);
  
  // Update shortcuts ref when shortcuts change
  useEffect(() => {
    shortcutsRef.current = shortcuts;
  }, [shortcuts]);

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;

    const { key, ctrlKey, altKey, shiftKey, metaKey } = event;
    
    // Create shortcut string
    const modifiers = [];
    if (ctrlKey) modifiers.push('ctrl');
    if (altKey) modifiers.push('alt');
    if (shiftKey) modifiers.push('shift');
    if (metaKey) modifiers.push('meta');
    
    const shortcutKey = [...modifiers, key.toLowerCase()].join('+');
    
    // Check if shortcut exists
    const callback = shortcutsRef.current[shortcutKey];
    if (callback) {
      event.preventDefault();
      event.stopPropagation();
      callback(event);
    }
  }, [enabled]);

  useEffect(() => {
    if (!target || !enabled) return;

    const element = target as EventTarget;
    element.addEventListener('keydown', handleKeyDown);

    return () => {
      element.removeEventListener('keydown', handleKeyDown);
    };
  }, [target, enabled, handleKeyDown]);
}

/**
 * Custom hook for handling single key presses
 * @param key - The key to listen for
 * @param callback - Function to call when key is pressed
 * @param options - Configuration options
 */
export function useKeyPress(
  key: string,
  callback: (event: KeyboardEvent) => void,
  options: UseKeyboardOptions & { keyEvent?: 'keydown' | 'keyup' } = {}
): void {
  const { target = document, enabled = true, keyEvent = 'keydown' } = options;
  const callbackRef = useRef(callback);
  
  // Update callback ref when callback changes
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const handleKeyEvent = useCallback((event: KeyboardEvent) => {
    if (!enabled) return;
    
    if (event.key.toLowerCase() === key.toLowerCase()) {
      callbackRef.current(event);
    }
  }, [key, enabled]);

  useEffect(() => {
    if (!target || !enabled) return;

    const element = target as EventTarget;
    element.addEventListener(keyEvent, handleKeyEvent);

    return () => {
      element.removeEventListener(keyEvent, handleKeyEvent);
    };
  }, [target, enabled, keyEvent, handleKeyEvent]);
}

/**
 * Custom hook for detecting if specific keys are currently pressed
 * @param keys - Array of keys to track
 * @returns Object with boolean values for each key
 */
export function useKeysPressed(keys: string[]): Record<string, boolean> {
  const [keysPressed, setKeysPressed] = useState<Record<string, boolean>>(
    keys.reduce((acc, key) => ({ ...acc, [key]: false }), {})
  );

  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    const key = event.key.toLowerCase();
    if (keys.includes(key)) {
      setKeysPressed(prev => ({ ...prev, [key]: true }));
    }
  }, [keys]);

  const handleKeyUp = useCallback((event: KeyboardEvent) => {
    const key = event.key.toLowerCase();
    if (keys.includes(key)) {
      setKeysPressed(prev => ({ ...prev, [key]: false }));
    }
  }, [keys]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  return keysPressed;
}

/**
 * Utility function to create shortcut string
 * @param shortcut - Shortcut configuration
 * @returns Formatted shortcut string
 */
export function createShortcutString(shortcut: KeyboardShortcut): string {
  const modifiers = [];
  if (shortcut.ctrl) modifiers.push('ctrl');
  if (shortcut.alt) modifiers.push('alt');
  if (shortcut.shift) modifiers.push('shift');
  if (shortcut.meta) modifiers.push('meta');
  
  return [...modifiers, shortcut.key.toLowerCase()].join('+');
}

/**
 * Utility function to format shortcut for display
 * @param shortcut - Shortcut string or configuration
 * @returns Human-readable shortcut string
 */
export function formatShortcut(shortcut: string | KeyboardShortcut): string {
  const shortcutStr = typeof shortcut === 'string' ? shortcut : createShortcutString(shortcut);
  
  return shortcutStr
    .split('+')
    .map(part => {
      switch (part) {
        case 'ctrl': return '⌃';
        case 'alt': return '⌥';
        case 'shift': return '⇧';
        case 'meta': return '⌘';
        default: return part.toUpperCase();
      }
    })
    .join('');
}