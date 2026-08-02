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
  by_source: { source: string; count: number }[]
  top_profiles: Profile[]
  incomplete_profiles: Profile[]
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
    request<Record<string, unknown>>('/api/import/url', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
