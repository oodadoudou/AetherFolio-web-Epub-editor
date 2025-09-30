// Application constants

// API Configuration
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  TIMEOUT: 30000, // 30 seconds
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000, // 1 second
} as const;

// File Configuration
export const FILE_CONFIG = {
  MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB
  ALLOWED_EPUB_EXTENSIONS: ['.epub'],
  ALLOWED_STANDALONE_TEXT_EXTENSIONS: ['.txt'],
  ALLOWED_IMAGE_EXTENSIONS: ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp'],
  ALLOWED_FONT_EXTENSIONS: ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
  ALLOWED_TEXT_EXTENSIONS: ['.html', '.xhtml', '.css', '.js', '.json', '.xml', '.txt', '.md'],
  CHUNK_SIZE: 1024 * 1024, // 1MB chunks for file upload
} as const;

// Combined allowed file extensions for general use
export const ALLOWED_FILE_EXTENSIONS = [
  ...FILE_CONFIG.ALLOWED_EPUB_EXTENSIONS,
  ...FILE_CONFIG.ALLOWED_STANDALONE_TEXT_EXTENSIONS,
  ...FILE_CONFIG.ALLOWED_IMAGE_EXTENSIONS,
  ...FILE_CONFIG.ALLOWED_FONT_EXTENSIONS,
  ...FILE_CONFIG.ALLOWED_TEXT_EXTENSIONS,
] as const;

// Upload allowed file extensions
export const UPLOAD_ALLOWED_EXTENSIONS = [
  ...FILE_CONFIG.ALLOWED_EPUB_EXTENSIONS,
  ...FILE_CONFIG.ALLOWED_STANDALONE_TEXT_EXTENSIONS,
] as const;

// UI Configuration
export const UI_CONFIG = {
  SIDEBAR_MIN_WIDTH: 200,
  SIDEBAR_MAX_WIDTH: 600,
  SIDEBAR_DEFAULT_WIDTH: 300,
  PANEL_MIN_HEIGHT: 100,
  PANEL_MAX_HEIGHT: 800,
  PANEL_DEFAULT_HEIGHT: 300,
  DEBOUNCE_DELAY: 300,
  TOAST_DURATION: 4000,
  MODAL_ANIMATION_DURATION: 200,
} as const;

// Timing Constants
export const DEBOUNCE_DELAY = 300;
export const THROTTLE_DELAY = 100;
export const AUTO_SAVE_DELAY = 30000;

// Search Configuration
export const SEARCH_CONFIG = {
  MAX_RESULTS: 1000,
  RESULTS_PER_PAGE: 50,
  HIGHLIGHT_CLASS: 'search-highlight',
  CURRENT_HIGHLIGHT_CLASS: 'search-highlight-current',
  DEBOUNCE_DELAY: 500,
  MIN_QUERY_LENGTH: 1,
} as const;

// Editor Configuration
export const EDITOR_CONFIG = {
  DEFAULT_THEME: 'vs-light',
  DARK_THEME: 'vs-dark',
  FONT_SIZE_MIN: 10,
  FONT_SIZE_MAX: 30,
  FONT_SIZE_DEFAULT: 14,
  TAB_SIZE: 2,
  AUTO_SAVE_DELAY: 2000,
  WORD_WRAP: true,
  LINE_NUMBERS: true,
  MINIMAP: false,
} as const;

// Theme Configuration
export const THEME_CONFIG = {
  LIGHT: 'light',
  DARK: 'dark',
  AUTO: 'auto',
  STORAGE_KEY: 'aetherfolio-theme',
} as const;

// Local Storage Keys
export const STORAGE_KEYS = {
  THEME: 'aetherfolio-theme',
  SIDEBAR_WIDTH: 'aetherfolio-sidebar-width',
  PANEL_HEIGHT: 'aetherfolio-panel-height',
  EDITOR_SETTINGS: 'aetherfolio-editor-settings',
  RECENT_FILES: 'aetherfolio-recent-files',
  USER_PREFERENCES: 'aetherfolio-user-preferences',
} as const;

// EPUB Specific Constants
export const EPUB_CONFIG = {
  MIME_TYPE: 'application/epub+zip',
  CONTAINER_PATH: 'META-INF/container.xml',
  PACKAGE_DOCUMENT_MEDIA_TYPE: 'application/oebps-package+xml',
  NCX_MEDIA_TYPE: 'application/x-dtbncx+xml',
  XHTML_MEDIA_TYPE: 'application/xhtml+xml',
  HTML_MEDIA_TYPE: 'text/html',
  CSS_MEDIA_TYPE: 'text/css',
  JS_MEDIA_TYPE: 'application/javascript',
  DEFAULT_LANGUAGE: 'en',
  DEFAULT_ENCODING: 'utf-8',
} as const;

// File Type Categories
export const FILE_CATEGORIES = {
  TEXT: 'text',
  IMAGE: 'image',
  FONT: 'font',
  STYLE: 'style',
  SCRIPT: 'script',
  DATA: 'data',
  OTHER: 'other',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error occurred. Please check your connection.',
  FILE_TOO_LARGE: 'File size exceeds the maximum allowed limit.',
  INVALID_FILE_TYPE: 'Invalid file type. Please select a valid EPUB or TEXT file.',
  UPLOAD_FAILED: 'File upload failed. Please try again.',
  SAVE_FAILED: 'Failed to save file. Please try again.',
  LOAD_FAILED: 'Failed to load file. Please try again.',
  SESSION_EXPIRED: 'Your session has expired. Please refresh the page.',
  INVALID_REGEX: 'Invalid regular expression pattern.',
  SEARCH_FAILED: 'Search operation failed. Please try again.',
  REPLACE_FAILED: 'Replace operation failed. Please try again.',
  EXPORT_FAILED: 'Export operation failed. Please try again.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  FILE_UPLOADED: 'File uploaded successfully.',
  FILE_SAVED: 'File saved successfully.',
  FILE_DELETED: 'File deleted successfully.',
  FILE_RENAMED: 'File renamed successfully.',
  SEARCH_COMPLETED: 'Search completed.',
  REPLACE_COMPLETED: 'Replace operation completed.',
  EXPORT_COMPLETED: 'Export completed successfully.',
  SETTINGS_SAVED: 'Settings saved successfully.',
} as const;

// Keyboard Shortcuts
export const KEYBOARD_SHORTCUTS = {
  SAVE: 'Ctrl+S',
  SAVE_MAC: 'Cmd+S',
  FIND: 'Ctrl+F',
  FIND_MAC: 'Cmd+F',
  REPLACE: 'Ctrl+H',
  REPLACE_MAC: 'Cmd+H',
  NEW_FILE: 'Ctrl+N',
  NEW_FILE_MAC: 'Cmd+N',
  OPEN_FILE: 'Ctrl+O',
  OPEN_FILE_MAC: 'Cmd+O',
  CLOSE_TAB: 'Ctrl+W',
  CLOSE_TAB_MAC: 'Cmd+W',
  TOGGLE_SIDEBAR: 'Ctrl+B',
  TOGGLE_SIDEBAR_MAC: 'Cmd+B',
  TOGGLE_PREVIEW: 'Ctrl+P',
  TOGGLE_PREVIEW_MAC: 'Cmd+P',
  FULLSCREEN: 'F11',
  ESCAPE: 'Escape',
} as const;

// Animation Durations
export const ANIMATION_DURATION = {
  FAST: 150,
  NORMAL: 300,
  SLOW: 500,
} as const;

// Z-Index Layers
export const Z_INDEX = {
  DROPDOWN: 1000,
  STICKY: 1020,
  FIXED: 1030,
  MODAL_BACKDROP: 1040,
  MODAL: 1050,
  POPOVER: 1060,
  TOOLTIP: 1070,
  TOAST: 1080,
} as const;

// Breakpoints (matching Tailwind CSS)
export const BREAKPOINTS = {
  SM: 640,
  MD: 768,
  LG: 1024,
  XL: 1280,
  '2XL': 1536,
} as const;

// Color Palette
export const COLORS = {
  PRIMARY: '#1890ff',
  SUCCESS: '#52c41a',
  WARNING: '#faad14',
  ERROR: '#ff4d4f',
  INFO: '#1890ff',
  TEXT_PRIMARY: '#262626',
  TEXT_SECONDARY: '#8c8c8c',
  BORDER: '#d9d9d9',
  BACKGROUND: '#ffffff',
  BACKGROUND_SECONDARY: '#fafafa',
} as const;

// Regular Expressions
export const REGEX_PATTERNS = {
  URL: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$/,
  UUID: /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  FILENAME: /^[^<>:"/\\|?*]+$/,
  HTML_TAG: /<\/?[a-z][\s\S]*>/i,
  CSS_SELECTOR: /^[a-zA-Z0-9\s.,#:>+~[\]="'\-_]+$/,
} as const;