import { Message } from '../agent/types.js'
import { readFile, writeFile, mkdir, appendFile } from 'fs/promises'
import { dirname, join } from 'path'
import { existsSync } from 'fs'

export type TranscriptEntry = {
  type: string
  uuid: string
  parentUuid: string | null
  timestamp: number
  data: unknown
}

export type SessionMetadata = {
  sessionId: string
  title?: string
  createdAt: number
  updatedAt: number
  projectDir: string
}

export class SessionStorage {
  private sessionDir: string

  constructor(sessionDir: string) {
    this.sessionDir = sessionDir
  }

  getSessionPath(sessionId: string): string {
    return join(this.sessionDir, `${sessionId}.jsonl`)
  }

  getMetadataPath(sessionId: string): string {
    return join(this.sessionDir, 'metadata', `${sessionId}.json`)
  }

  async appendMessage(sessionId: string, message: Message): Promise<void> {
    const logPath = this.getSessionPath(sessionId)
    await mkdir(dirname(logPath), { recursive: true })

    const entry: TranscriptEntry = {
      type: message.type,
      uuid: message.uuid,
      parentUuid: message.parentUuid,
      timestamp: message.timestamp,
      data: message,
    }

    const line = JSON.stringify(entry) + '\n'
    await appendFile(logPath, line, 'utf-8')
  }

  async loadSession(sessionId: string): Promise<Message[]> {
    const logPath = this.getSessionPath(sessionId)

    if (!existsSync(logPath)) {
      return []
    }

    const content = await readFile(logPath, 'utf-8')
    const lines = content.trim().split('\n').filter(line => line.length > 0)

    const messages: Message[] = []
    for (const line of lines) {
      try {
        const entry: TranscriptEntry = JSON.parse(line)
        messages.push(entry.data as Message)
      } catch {
        console.warn(`Failed to parse line`)
      }
    }

    return messages
  }

  async saveMetadata(metadata: SessionMetadata): Promise<void> {
    const metadataPath = this.getMetadataPath(metadata.sessionId)
    await mkdir(dirname(metadataPath), { recursive: true })
    await writeFile(metadataPath, JSON.stringify(metadata, null, 2), 'utf-8')
  }

  async loadMetadata(sessionId: string): Promise<SessionMetadata | null> {
    const metadataPath = this.getMetadataPath(sessionId)

    if (!existsSync(metadataPath)) {
      return null
    }

    const content = await readFile(metadataPath, 'utf-8')
    return JSON.parse(content) as SessionMetadata
  }

  extractTitle(messages: Message[]): string | null {
    for (const msg of messages) {
      if (msg.type === 'user') {
        const text = this.extractTextContent(msg.message.content)
        if (text && text.length > 0) {
          return text.length > 50 ? text.slice(0, 50) + '...' : text
        }
      }
    }
    return null
  }

  private extractTextContent(content: unknown): string {
    if (typeof content === 'string') {
      return content
    }
    if (Array.isArray(content)) {
      return content
        .filter((c: any) => c.type === 'text')
        .map((c: any) => c.text)
        .join(' ')
    }
    return ''
  }
}
