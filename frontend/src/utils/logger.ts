type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'none'

const LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  none: 4,
}

const currentLevel: LogLevel =
  (import.meta.env.VITE_LOG_LEVEL as LogLevel) || (import.meta.env.DEV ? 'debug' : 'warn')

function shouldLog(level: LogLevel): boolean {
  return LEVEL_PRIORITY[level] >= LEVEL_PRIORITY[currentLevel]
}

export const logger = {
  debug: (msg: string, ...args: unknown[]) => {
    if (shouldLog('debug')) console.debug(`[DEBUG] ${msg}`, ...args)
  },
  info: (msg: string, ...args: unknown[]) => {
    if (shouldLog('info')) console.log(`[INFO] ${msg}`, ...args)
  },
  warn: (msg: string, ...args: unknown[]) => {
    if (shouldLog('warn')) console.warn(`[WARN] ${msg}`, ...args)
  },
  error: (msg: string, ...args: unknown[]) => {
    if (shouldLog('error')) console.error(`[ERROR] ${msg}`, ...args)
  },
}
