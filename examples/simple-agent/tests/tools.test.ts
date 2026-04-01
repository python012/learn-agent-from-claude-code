import { describe, it, expect } from 'vitest'
import { BashTool } from '../src/tools/BashTool.js'
import { FileReadTool } from '../src/tools/FileReadTool.js'
import { FileWriteTool } from '../src/tools/FileWriteTool.js'

describe('Built-in Tools', () => {
  describe('BashTool', () => {
    it('should have correct name and description', () => {
      expect(BashTool.name).toBe('Bash')
      expect(BashTool.description).toContain('bash')
    })

    it('should be concurrency unsafe', () => {
      expect(BashTool.isConcurrencySafe()).toBe(false)
    })

    it('should be read-only false', () => {
      expect(BashTool.isReadOnly()).toBe(false)
    })
  })

  describe('FileReadTool', () => {
    it('should have correct name and description', () => {
      expect(FileReadTool.name).toBe('FileRead')
      expect(FileReadTool.description).toContain('Read')
    })

    it('should be concurrency safe', () => {
      expect(FileReadTool.isConcurrencySafe()).toBe(true)
    })

    it('should be read-only', () => {
      expect(FileReadTool.isReadOnly()).toBe(true)
    })
  })

  describe('FileWriteTool', () => {
    it('should have correct name and description', () => {
      expect(FileWriteTool.name).toBe('FileWrite')
      expect(FileWriteTool.description).toContain('Write')
    })

    it('should be concurrency unsafe', () => {
      expect(FileWriteTool.isConcurrencySafe()).toBe(false)
    })

    it('should be read-only false', () => {
      expect(FileWriteTool.isReadOnly()).toBe(false)
    })
  })
})
