// Custom hook for WebSocket connection management

import { useState, useEffect, useCallback, useRef } from 'react';
import { useAppStore } from '../store';

export interface WebSocketMessage {
  type: string;
  payload?: any;
  timestamp?: number;
}

export interface WebSocketOptions {
  url?: string;
  protocols?: string | string[];
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
}

export interface UseWebSocketReturn {
  socket: WebSocket | null;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: WebSocketMessage) => boolean;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  isConnected: boolean;
  isConnecting: boolean;
}

/**
 * Custom hook for WebSocket connection management
 * @param options - WebSocket configuration options
 * @returns WebSocket state and actions
 */
export function useWebSocket(options: WebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = process.env.VITE_WS_URL || 'ws://localhost:8080/ws',
    protocols,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    heartbeatInterval = 30000,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  // Get store actions
  const { setConnected, updateLastActivity } = useAppStore();

  // Clear timeouts
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Send heartbeat
  const sendHeartbeat = useCallback(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      const heartbeatMessage: WebSocketMessage = {
        type: 'heartbeat',
        timestamp: Date.now(),
      };
      socket.send(JSON.stringify(heartbeatMessage));
      
      // Schedule next heartbeat
      heartbeatTimeoutRef.current = setTimeout(sendHeartbeat, heartbeatInterval);
    }
  }, [socket, heartbeatInterval]);

  // Send message
  const sendMessage = useCallback((message: WebSocketMessage): boolean => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected');
      return false;
    }

    try {
      const messageWithTimestamp = {
        ...message,
        timestamp: message.timestamp || Date.now(),
      };
      socket.send(JSON.stringify(messageWithTimestamp));
      updateLastActivity();
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }, [socket, updateLastActivity]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (socket && socket.readyState === WebSocket.CONNECTING) {
      return; // Already connecting
    }

    try {
      setConnectionState('connecting');
      const ws = new WebSocket(url, protocols);

      ws.onopen = (event) => {
        console.log('WebSocket connected');
        setConnectionState('connected');
        setConnected(true);
        updateLastActivity();
        reconnectAttemptsRef.current = 0;
        
        // Start heartbeat
        if (heartbeatInterval > 0) {
          heartbeatTimeoutRef.current = setTimeout(sendHeartbeat, heartbeatInterval);
        }
        
        onOpen?.(event);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setConnectionState('disconnected');
        setConnected(false);
        clearTimeouts();
        
        // Attempt reconnection if enabled and not manually closed
        if (shouldReconnectRef.current && 
            reconnectAttemptsRef.current < reconnectAttempts &&
            event.code !== 1000) { // 1000 = normal closure
          
          reconnectAttemptsRef.current++;
          console.log(`Attempting to reconnect (${reconnectAttemptsRef.current}/${reconnectAttempts})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
        
        onClose?.(event);
      };

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setConnectionState('error');
        setConnected(false);
        onError?.(event);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          updateLastActivity();
          
          // Handle heartbeat response
          if (message.type === 'heartbeat') {
            return; // Don't pass heartbeat messages to user handler
          }
          
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      setSocket(ws);
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState('error');
    }
  }, [url, protocols, reconnectAttempts, reconnectInterval, heartbeatInterval, sendHeartbeat, setConnected, updateLastActivity, onOpen, onClose, onError, onMessage, clearTimeouts]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    clearTimeouts();
    
    if (socket) {
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close(1000, 'Manual disconnect');
      }
      setSocket(null);
    }
    
    setConnectionState('disconnected');
    setConnected(false);
  }, [socket, setConnected, clearTimeouts]);

  // Reconnect to WebSocket
  const reconnect = useCallback(() => {
    disconnect();
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    
    // Small delay to ensure cleanup is complete
    setTimeout(() => {
      connect();
    }, 100);
  }, [disconnect, connect]);

  // Auto-connect on mount
  useEffect(() => {
    if (url) {
      connect();
    }
    
    return () => {
      shouldReconnectRef.current = false;
      disconnect();
    };
  }, [url]); // Only reconnect when URL changes

  // Handle page visibility changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page is hidden, pause heartbeat
        clearTimeouts();
      } else {
        // Page is visible, resume connection if needed
        if (socket && socket.readyState === WebSocket.OPEN && heartbeatInterval > 0) {
          heartbeatTimeoutRef.current = setTimeout(sendHeartbeat, heartbeatInterval);
        } else if (!socket || socket.readyState === WebSocket.CLOSED) {
          // Reconnect if connection was lost
          reconnect();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [socket, heartbeatInterval, sendHeartbeat, reconnect, clearTimeouts]);

  // Handle online/offline events
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => {
      console.log('Network connection restored');
      if (!socket || socket.readyState === WebSocket.CLOSED) {
        reconnect();
      }
    };

    const handleOffline = () => {
      console.log('Network connection lost');
      clearTimeouts();
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [socket, reconnect, clearTimeouts]);

  return {
    socket,
    connectionState,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    reconnect,
    isConnected: connectionState === 'connected',
    isConnecting: connectionState === 'connecting',
  };
}

/**
 * Custom hook for handling specific WebSocket message types
 * @param messageType - The message type to listen for
 * @param handler - Handler function for the message
 * @param options - WebSocket options
 */
export function useWebSocketMessage(
  messageType: string,
  handler: (payload: any) => void,
  options: WebSocketOptions = {}
): UseWebSocketReturn {
  const webSocket = useWebSocket({
    ...options,
    onMessage: (message) => {
      if (message.type === messageType) {
        handler(message.payload);
      }
      options.onMessage?.(message);
    },
  });

  return webSocket;
}