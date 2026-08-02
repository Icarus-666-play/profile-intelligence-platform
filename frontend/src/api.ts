/** Thin REST client for the FastAPI surface. */

export type Profile = {
  id: number
  external_id: string | null
  display_name: string
  email: string | null
  phone: string | null
  title: string | null
  organization: string | null
  location: string | null
  tags: string[]
  source: string | null
  notes: string | null
  score: number | null
  created_at: string | null
  updated_at: string | null
}

export type DashboardSnapshot = {
  total_profiles: number
  scored_profiles: number
  average_score: number | null
  imported_today: number
  countries: number
  average_price: number | null
  average_price_currency: string
  average_rating: number | null
  by_source: { source: string; count: number }[]
  top_profiles: Profile[]
  incomplete_profiles: Profile[]
  newest_profiles: Profile[]
  latest_imports: {
    path: string
    name: string
    imported_at: string | null
    file_size: number
  }[]
  duplicates: {
    left_id: number
    right_id: number
    left_name: string
    right_name: string
    score: number
  }[]
  import_queue: {
    path: string
    name: string
    file_size: number
  }[]
}

export type PluginInfo = {
  name: string
  description: string
  supported_extensions: string[]
}

export type Comparison = {
  left_id: number
  right_id: number
  left_name: string
  right_name: string
  differences: number
  matches: number
  fields: {
    field: string
    left: unknown
    right: unknown
    equal: boolean
  }[]
}

export type Analytics = {
  profiles: number
  scored_profiles: number
  average_score: number | null
  by_source: { source: string; count: number }[]
  duplicates: {
    scanned: number
    pairs: number
    groups: number
    threshold: number
  }
  classification: {
    count: number
    confidence_bands: Record<string, number>
    completeness: Record<string, number>
  }
}

export type ImportSummary = {
  path: string
  plugin: string
  records_read: number
  created: number
  updated: number
  skipped: number
  written: number
  success: boolean
  errors: string[]
  url?: string
  downloaded_path?: string
  status?: string
}

export type ImportPreview = {
  path: string
  plugin: string
  records_read: number
  accepted_count: number
  rejected_count: number
  duplicate_count: number
  update_count: number
  ok: boolean
  errors: string[]
  stages_run: string[]
  rows: ImportPreviewRow[]
  url?: string
  downloaded_path?: string
}

export type ImportPreviewRow = {
  index: number
  display_name: string
  email: string | null
  organization: string | null
  source: string | null
  score: number | null
  status: string
  messages: string[]
  picture: string | null
  age: string | null
  nationality: string | null
  languages: string[]
  services: string[]
  rates: string[]
  reviews: string[]
  pictures: string[]
  location: string | null
}

export type ImportActivity = {
  recent_urls: { url: string; at: string }[]
  import_queue: { path: string; name: string; file_size: number }[]
  progress: {
    url: string
    stage: string
    message: string
    started_at: string
    percent: number
  } | null
  errors: { url: string; message: string; at: string }[]
  completed: {
    url: string
    path: string | null
    plugin: string | null
    created: number
    updated: number
    success: boolean
    message: string | null
    at: string
  }[]
}

export type AuthStatus = {
  enabled: boolean
  allow_guest: boolean
  username_hint: string | null
  flow: string[]
}

export type AuthSession = {
  token: string
  username: string
  mode: string
  expires_at: number
  authenticated: boolean
  guest: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
    ...init,
  })
  const payload = (await response.json()) as T & { error?: string; status?: number }
  if (!response.ok) {
    throw new Error(payload.error || `HTTP ${response.status}`)
  }
  return payload
}

export const api = {
  health: () => request<{ status: string; stack: string }>('/api/health'),
  dashboard: () => request<DashboardSnapshot>('/api/dashboard'),
  profiles: (params?: { q?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams()
    if (params?.q) query.set('q', params.q)
    if (params?.limit != null) query.set('limit', String(params.limit))
    if (params?.offset != null) query.set('offset', String(params.offset))
    const suffix = query.toString() ? `?${query}` : ''
    return request<{ total: number; items: Profile[] }>(`/api/profiles${suffix}`)
  },
  profile: (id: number) => request<Profile>(`/api/profiles/${id}`),
  compare: (leftId: number, rightId: number) =>
    request<Comparison>('/api/compare', {
      method: 'POST',
      body: JSON.stringify({ left_id: leftId, right_id: rightId }),
    }),
  analytics: () => request<Analytics>('/api/analytics'),
  plugins: () => request<{ count: number; items: PluginInfo[] }>('/api/plugins'),
  reloadPlugins: () =>
    request<{ reloaded: number; items: PluginInfo[] }>('/api/plugins/reload', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  importFiles: (body: {
    paths?: string[]
    files?: { name: string; content_base64: string }[]
    plugin?: string
    source?: string
    recursive?: boolean
  }) =>
    request<{ count: number; imports: unknown[]; errors: string[] }>(
      '/api/import/files',
      { method: 'POST', body: JSON.stringify(body) },
    ),
  importUrl: (body: { url: string; plugin?: string; source?: string }) =>
    request<ImportSummary>('/api/import/url', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  previewUrl: (body: { url: string; plugin?: string; source?: string }) =>
    request<ImportPreview>('/api/import/url/preview', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  importActivity: () => request<ImportActivity>('/api/import/activity'),
  authStatus: () => request<AuthStatus>('/api/auth/status'),
  login: (username: string, password: string) =>
    request<{ session: AuthSession; next: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  guest: () =>
    request<{ session: AuthSession; next: string }>('/api/auth/guest', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  logout: (token: string | null) =>
    request<{ ok: boolean; next: string }>('/api/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ token }),
    }),
  authSession: (token: string) =>
    request<{ session: AuthSession | null }>(
      `/api/auth/session?token=${encodeURIComponent(token)}`,
    ),
}
