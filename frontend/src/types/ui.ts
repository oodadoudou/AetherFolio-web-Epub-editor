// UI related type definitions

export type Theme = 'light' | 'dark' | 'auto';

export type PanelPosition = 'left' | 'right' | 'top' | 'bottom';

export type PanelSize = 'small' | 'medium' | 'large' | 'auto';

export interface PanelConfig {
  id: string;
  title: string;
  position: PanelPosition;
  size: PanelSize;
  isVisible: boolean;
  isCollapsed: boolean;
  isResizable: boolean;
  isDraggable: boolean;
  minWidth?: number;
  maxWidth?: number;
  minHeight?: number;
  maxHeight?: number;
}

export interface ModalConfig {
  id: string;
  title: string;
  isVisible: boolean;
  isClosable: boolean;
  isFullscreen: boolean;
  width?: number | string;
  height?: number | string;
  zIndex?: number;
}

export interface ToastConfig {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  isClosable?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ContextMenuItem {
  id: string;
  label: string;
  icon?: string;
  shortcut?: string;
  disabled?: boolean;
  divider?: boolean;
  children?: ContextMenuItem[];
  onClick?: () => void;
}

export interface ContextMenuConfig {
  items: ContextMenuItem[];
  position: {
    x: number;
    y: number;
  };
  isVisible: boolean;
}

export interface ToolbarItem {
  id: string;
  type: 'button' | 'separator' | 'dropdown' | 'input' | 'custom';
  label?: string;
  icon?: string;
  tooltip?: string;
  disabled?: boolean;
  active?: boolean;
  onClick?: () => void;
  children?: ToolbarItem[];
}

export interface ToolbarConfig {
  id: string;
  position: 'top' | 'bottom' | 'left' | 'right';
  items: ToolbarItem[];
  isVisible: boolean;
  isCollapsed: boolean;
}

export interface LayoutConfig {
  panels: PanelConfig[];
  toolbars: ToolbarConfig[];
  theme: Theme;
  isFullscreen: boolean;
  sidebarWidth: number;
  bottomPanelHeight: number;
}

export interface KeyboardShortcut {
  id: string;
  keys: string[];
  description: string;
  action: () => void;
  context?: string;
  disabled?: boolean;
}

export interface ProgressConfig {
  id: string;
  type: 'linear' | 'circular';
  value: number;
  max: number;
  label?: string;
  showPercentage?: boolean;
  color?: string;
  size?: 'small' | 'medium' | 'large';
}

export interface LoadingState {
  isLoading: boolean;
  message?: string;
  progress?: number;
  cancelable?: boolean;
  onCancel?: () => void;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  details?: string;
  recoverable?: boolean;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export interface ViewState {
  loading: LoadingState;
  error: ErrorState;
  isEmpty: boolean;
  isInitialized: boolean;
}