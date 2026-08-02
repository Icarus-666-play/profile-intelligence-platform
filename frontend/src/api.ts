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
  tags: string[] | string | null
  source: string | null
  notes: string | null
  score: number | null
  created_at: string | null
  updated_at: string | null
  photo: string | null
  age: string | null
  country: string | null
  languages: string[]
  rating: number | null
  average_price: number | null
  average_price_currency: string | null
  imported: string | null
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

export type NamedCount = {
  name: string
  count: number
}

export type AveragePriceBucket = {
  label: string
  average: number
  currency: string
  count: number
}

export type PeriodCount = {
  period: string
  count: number
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
  countries: NamedCount[]
  average_prices: AveragePriceBucket[]
  languages: NamedCount[]
  services: NamedCount[]
  duplicate_pairs: {
    left_id: number
    right_id: number
    left_name: string
    right_name: string
    score: number
  }[]
  monthly_imports: PeriodCount[]
  import_trend: PeriodCount[]
}

export type UrlSnapshot = {
  path: string
  source: string
  content_type: string | null
  from_cache: boolean
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
  snapshot?: UrlSnapshot
  pipeline?: string[]
  stages_run?: string[]
  stage?: string
  percent?: number
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
  snapshot?: UrlSnapshot
  pipeline?: string[]
  stage?: string
  percent?: number
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
    stages_run?: string[]
    pipeline?: string[]
    snapshot?: UrlSnapshot | null
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
  pipeline?: string[]
  stage_labels?: Record<string, string>
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

export type SettingsSnapshot = {
  theme: {
    options: string[]
    note: string
    source: string
  }
  database: {
    driver: string
    path: string
    url: string | null
    echo_sql: boolean
    timeout_seconds: number
    foreign_keys: boolean
    check_same_thread: boolean
    exists: boolean
  }
  plugins: {
    directory: string
    auto_discover: boolean
    enabled: string[]
    note: string
    count?: number
    items?: PluginInfo[]
  }
  scoring: {
    method: string
    max_score: number
    weights: Record<string, number>
    daily_rescore: boolean
    config_file: string
  }
  import_folder: {
    path: string
    configured: string
    recursive: boolean
    excel_path: string
    dashboard_path: string
    exists: boolean
  }
  playwright: {
    available: boolean
    enabled: boolean
    status: string
    note: string
  }
  backups: {
    directory: string
    log_backup_count: number
    note: string
    items: {
      name: string
      path: string
      size_bytes: number
      created_at: string | null
    }[]
  }
  meta: {
    app: string
    version: string
    environment: string
    config_dir: string | null
    root_dir: string
  }
}

export type DailySnapshot = {
  pipeline: string[]
  stage_labels: Record<string, string>
  progress: {
    stage: string
    message: string
    percent: number
    stages_run: string[]
    pipeline: string[]
    status: string
  } | null
  last_result: DailyRunResult | null
}

export type DailyRunResult = {
  ok: boolean
  success: boolean
  pipeline: string[]
  stage_labels: Record<string, string>
  stages_run: string[]
  stage: string
  percent: number
  message: string
  import_folder?: string
  files_detected: number
  files_new: number
  files_imported: number
  created: number
  updated: number
  skipped: number
  profile_count: number
  excel_path?: string | null
  dashboard_path?: string | null
  errors: string[]
}

export const api = {
  health: () => request<{ status: string; stack: string }>('/api/health'),
  dashboard: () => request<DashboardSnapshot>('/api/dashboard'),
  daily: () => request<DailySnapshot>('/api/daily'),
  runDaily: (body?: {
    import_dir?: string
    excel_path?: string
    dashboard_path?: string
    force_all_files?: boolean
  }) =>
    request<DailyRunResult>('/api/daily/run', {
      method: 'POST',
      body: JSON.stringify(body ?? {}),
    }),
  settings: () => request<SettingsSnapshot>('/api/settings'),
  backups: () =>
    request<{
      directory: string
      count: number
      items: SettingsSnapshot['backups']['items']
    }>('/api/backups'),
  createBackup: () =>
    request<{
      ok: boolean
      backup: SettingsSnapshot['backups']['items'][number]
    }>('/api/backups', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
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
  importUrl: (body: {
    url?: string
    urls?: string[]
    plugin?: string
    source?: string
  }) =>
    request<ImportSummary & {
      count?: number
      imports?: ImportSummary[]
      errors?: string[]
      urls?: string[]
      ok?: boolean
    }>('/api/import/url', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  previewUrl: (body: {
    url?: string
    urls?: string[]
    plugin?: string
    source?: string
  }) =>
    request<ImportPreview & {
      count?: number
      previews?: ImportPreview[]
      errors?: string[]
      urls?: string[]
    }>('/api/import/url/preview', {
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
