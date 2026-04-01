import { Message } from '../agent/types.js'

export type AppState = {
  sessionId: string
  messages: Message[]
  pendingToolCalls: Array<{
    id: string
    name: string
    input: Record<string, unknown>
  }>
  isProcessing: boolean
  tokenUsage: {
    inputTokens: number
    outputTokens: number
  }
}

export type StateStore = {
  getState: () => AppState
  setState: (updater: AppState | ((prev: AppState) => AppState)) => void
  subscribe: (listener: () => void) => () => void
}

export function createStateStore(initialState?: Partial<AppState>): StateStore {
  let state: AppState = {
    sessionId: crypto.randomUUID(),
    messages: [],
    pendingToolCalls: [],
    isProcessing: false,
    tokenUsage: {
      inputTokens: 0,
      outputTokens: 0,
    },
    ...initialState,
  }

  const listeners = new Set<() => void>()

  return {
    getState: () => state,

    setState: (updater) => {
      const oldState = state
      const newState = typeof updater === 'function'
        ? (updater as (prev: AppState) => AppState)(oldState)
        : updater

      if (Object.is(oldState, newState)) {
        return
      }

      state = newState
      listeners.forEach(listener => listener())
    },

    subscribe: (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}
