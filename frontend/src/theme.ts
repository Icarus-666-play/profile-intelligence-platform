/** Browser-local theme preference for Settings → Theme. */

export const THEME_KEY = 'pip.theme'

export const THEMES = [
  {
    id: 'default',
    label: 'Default',
    note: 'Teal mist — the product default.',
  },
  {
    id: 'harbor',
    label: 'Harbor',
    note: 'Cool slate ink with a marine accent.',
  },
  {
    id: 'forest',
    label: 'Forest',
    note: 'Deep green countryside accents.',
  },
] as const

export type ThemeId = (typeof THEMES)[number]['id']

export function readTheme(): ThemeId {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === 'harbor' || stored === 'forest' || stored === 'default') {
    return stored
  }
  return 'default'
}

export function applyTheme(theme: ThemeId) {
  document.documentElement.dataset.theme = theme === 'default' ? '' : theme
  if (!document.documentElement.dataset.theme) {
    document.documentElement.removeAttribute('data-theme')
  }
  localStorage.setItem(THEME_KEY, theme)
}
