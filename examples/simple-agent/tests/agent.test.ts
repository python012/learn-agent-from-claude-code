import { describe, it, expect } from 'vitest'
import { createStateStore } from '../src/state/StateStore.js'

describe('StateStore', () => {
  it('should initialize with default state', () => {
    const store = createStateStore()
    const state = store.getState()

    expect(state.sessionId).toBeDefined()
    expect(state.messages).toEqual([])
    expect(state.pendingToolCalls).toEqual([])
    expect(state.isProcessing).toBe(false)
    expect(state.tokenUsage).toEqual({
      inputTokens: 0,
      outputTokens: 0,
    })
  })

  it('should accept initial state', () => {
    const store = createStateStore({
      sessionId: 'test-id',
      tokenUsage: {
        inputTokens: 100,
        outputTokens: 50,
      },
    })

    const state = store.getState()
    expect(state.sessionId).toBe('test-id')
    expect(state.tokenUsage.inputTokens).toBe(100)
  })

  it('should update state with setState', () => {
    const store = createStateStore()

    store.setState(prev => ({
      ...prev,
      isProcessing: true,
    }))

    expect(store.getState().isProcessing).toBe(true)
  })

  it('should notify subscribers on state change', () => {
    const store = createStateStore()
    let notifyCount = 0

    const unsubscribe = store.subscribe(() => {
      notifyCount++
    })

    store.setState(prev => ({ ...prev, isProcessing: true }))
    store.setState(prev => ({ ...prev, isProcessing: false }))

    expect(notifyCount).toBe(2)

    unsubscribe()

    store.setState(prev => ({ ...prev, isProcessing: true }))
    expect(notifyCount).toBe(2)
  })
})
