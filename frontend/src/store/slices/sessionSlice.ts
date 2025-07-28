// Session state slice
// Manages session-related state

import { StateCreator } from 'zustand';

export interface SessionState {
  sessionId: string | null;
  isConnected: boolean;
  lastActivity: Date | null;
}

export interface SessionActions {
  setSessionId: (sessionId: string) => void;
  setConnected: (connected: boolean) => void;
  updateLastActivity: () => void;
  clearSession: () => void;
}

export type SessionSlice = SessionState & SessionActions;

export const createSessionSlice: StateCreator<SessionSlice> = (set) => ({
  // State
  sessionId: null,
  isConnected: false,
  lastActivity: null,

  // Actions
  setSessionId: (sessionId: string) => set({ sessionId }),
  setConnected: (connected: boolean) => set({ isConnected: connected }),
  updateLastActivity: () => set({ lastActivity: new Date() }),
  clearSession: () => set({ 
    sessionId: null, 
    isConnected: false, 
    lastActivity: null 
  }),
});