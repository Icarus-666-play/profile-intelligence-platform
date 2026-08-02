/** Parse one-URL-per-line import lists. */

const PLACEHOLDER = /^(https?:\/\/)?(\.\.\.|…)?$/i

export function parseUrlList(text: string): string[] {
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n')
  const urls: string[] = []
  const seen = new Set<string>()
  for (const line of lines) {
    const value = line.trim()
    if (!value || PLACEHOLDER.test(value) || value === 'https://...' || value === 'http://...') {
      continue
    }
    if (!/^https?:\/\/.+/i.test(value)) {
      continue
    }
    if (seen.has(value)) continue
    seen.add(value)
    urls.push(value)
  }
  return urls
}

export const URL_LIST_PLACEHOLDER = [
  'https://...',
  'https://...',
  'https://...',
  'https://...',
].join('\n')
