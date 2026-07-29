import type {
  AiCapabilities,
  ApiMessage,
  ChatMessage,
  ContractorBrief,
  DashboardSummary,
  DesignRequirements,
  DesignScore,
  DesignVersion,
  HomeProfile,
  Inspiration,
  Professional,
  RegionConstraint,
  RegionAction,
  Room,
  SessionUser,
  SpaceCheck,
  TokenResponse,
} from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

type RequestOptions = {
  method?: string
  token?: string | null
  body?: unknown
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers()
  headers.set('Content-Type', 'application/json')

  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  if (!response.ok) {
    const fallbackMessage = 'Something went wrong while calling the API.'
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      const errorPayload = (await response.json()) as { detail?: string | Array<{ msg?: string }> }
      const detail = errorPayload.detail
      if (typeof detail === 'string') {
        throw new Error(detail)
      }
      if (Array.isArray(detail) && detail[0]?.msg) {
        throw new Error(detail.map((item) => item.msg).filter(Boolean).join(' '))
      }
      throw new Error(fallbackMessage)
    }
    throw new Error(fallbackMessage)
  }

  return (await response.json()) as T
}

async function uploadRequest<T>(path: string, token: string, file: File): Promise<T> {
  const formData = new FormData()
  formData.append('image', file)

  const headers = new Headers()
  headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    const fallbackMessage = 'Something went wrong while uploading the image.'
    const contentType = response.headers.get('content-type') ?? ''
    if (contentType.includes('application/json')) {
      const errorPayload = (await response.json()) as { detail?: string }
      throw new Error(errorPayload.detail ?? fallbackMessage)
    }
    throw new Error(fallbackMessage)
  }

  return (await response.json()) as T
}

export const api = {
  getAiCapabilities: () =>
    fetch(`${API_BASE_URL.replace(/\/api$/, '')}/api/system/ai-capabilities`).then(async (response) => {
      if (!response.ok) {
        throw new Error('Unable to load AI capabilities.')
      }
      return (await response.json()) as AiCapabilities
    }),
  getGenerationStatus: () =>
    fetch(`${API_BASE_URL.replace(/\/api$/, '')}/api/system/generation-status`).then(async (response) => {
      if (!response.ok) {
        throw new Error('Unable to load generation status.')
      }
      return (await response.json()) as {
        stage: string
        label: string
        busy: boolean
        step: number | null
        total_steps: number | null
        error: string | null
      }
    }),
  resetGeneration: () =>
    fetch(`${API_BASE_URL.replace(/\/api$/, '')}/api/system/generation-reset`, {
      method: 'POST',
    }).then(async (response) => {
      if (!response.ok) {
        throw new Error('Unable to clear the previous generation.')
      }
      return (await response.json()) as {
        stage: string
        label: string
        busy: boolean
        step: number | null
        total_steps: number | null
        error: string | null
      }
    }),
  signup: (payload: {
    name: string
    email: string
    phone: string
    city: string
    password: string
  }) => request<TokenResponse>('/auth/signup', { method: 'POST', body: payload }),
  login: (payload: { email: string; password: string }) =>
    request<TokenResponse>('/auth/login', { method: 'POST', body: payload }),
  me: (token: string) => request<TokenResponse>('/auth/me', { token }),
  getDashboard: (token: string) => request<DashboardSummary>('/dashboard/summary', { token }),
  getProfile: (token: string) => request<SessionUser>('/profile', { token }),
  updateProfile: (token: string, payload: { name: string; phone: string; city: string }) =>
    request<ApiMessage>('/profile', { method: 'PUT', token, body: payload }),
  getHome: (token: string) => request<HomeProfile>('/homes/me', { token }),
  updateHome: (token: string, payload: Omit<HomeProfile, 'id' | 'user_id'>) =>
    request<ApiMessage>('/homes/me', { method: 'PUT', token, body: payload }),
  listRooms: (token: string) => request<Room[]>('/rooms', { token }),
  createRoom: (
    token: string,
    payload: {
      room_type: string
      dimensions: { length: number; width: number; height: number }
      original_image_url?: string | null
      match_home_style: boolean
    },
  ) => request<Room>('/rooms', { method: 'POST', token, body: payload }),
  uploadRoomImage: (token: string, roomId: string, file: File) =>
    uploadRequest<Room>(`/rooms/${roomId}/upload`, token, file),
  getRoom: (token: string, roomId: string) => request<Room>(`/rooms/${roomId}`, { token }),
  sendChat: (token: string, roomId: string, payload: ChatMessage) =>
    request<ChatMessage[]>(`/rooms/${roomId}/chat`, { method: 'POST', token, body: payload }),
  getRequirements: (token: string, roomId: string) =>
    request<DesignRequirements>(`/rooms/${roomId}/requirements`, { token }),
  getConversation: (token: string, roomId: string) =>
    request<ChatMessage[]>(`/rooms/${roomId}/conversation`, { token }),
  updateRequirements: (token: string, roomId: string, payload: DesignRequirements) =>
    request<ApiMessage>(`/rooms/${roomId}/requirements`, {
      method: 'PUT',
      token,
      body: payload,
    }),
  getSpaceCheck: (token: string, roomId: string) =>
    request<SpaceCheck>(`/rooms/${roomId}/space-check`, { method: 'POST', token }),
  generateDesign: (
    token: string,
    roomId: string,
    quality?: 'preview' | 'balanced' | 'quality',
  ) =>
    request<DesignVersion>(`/rooms/${roomId}/generate`, {
      method: 'POST',
      token,
      body: quality ? { quality } : {},
    }),
  listDesigns: (token: string, roomId: string) =>
    request<DesignVersion[]>(`/rooms/${roomId}/designs`, { token }),
  reviseDesign: (
    token: string,
    roomId: string,
    designId: string,
    payload: ChatMessage,
  ) =>
    request<DesignVersion>(`/rooms/${roomId}/designs/${designId}/revise`, {
      method: 'POST',
      token,
      body: payload,
    }),
  getScore: (token: string, designId: string) =>
    request<DesignScore>(`/scores/${designId}`, { token }),
  generateBrief: (token: string, designId: string) =>
    request<ContractorBrief>(`/briefs/${designId}/generate`, { method: 'POST', token }),
  listBriefs: (token: string) => request<ContractorBrief[]>('/briefs', { token }),
  listInspirations: (token: string) => request<Inspiration[]>('/inspirations', { token }),
  addInspiration: (
    token: string,
    payload: { image_url: string; detected_tags: string[] },
  ) =>
    request<Inspiration>('/inspirations', { method: 'POST', token, body: payload }),
  listProfessionals: (query: { city?: string; profession?: string } = {}) => {
    const params = new URLSearchParams()
    if (query.city) params.set('city', query.city)
    if (query.profession) params.set('profession', query.profession)
    const suffix = params.toString() ? `?${params.toString()}` : ''
    return request<Professional[]>(`/professionals${suffix}`)
  },

  listRegionConstraints: (token: string, roomId: string) =>
    request<RegionConstraint[]>(`/rooms/${roomId}/region-constraints`, { token }),

  createRegionConstraint: (
    token: string,
    roomId: string,
    payload: {
      action: RegionAction
      label: string
      image_width: number
      image_height: number
      mask: File
    },
  ) => {
    const formData = new FormData()
    formData.append('action', payload.action)
    formData.append('label', payload.label)
    formData.append('image_width', String(payload.image_width))
    formData.append('image_height', String(payload.image_height))
    formData.append('mask', payload.mask)
    const headers = new Headers()
    headers.set('Authorization', `Bearer ${token}`)
    return fetch(`${API_BASE_URL}/rooms/${roomId}/region-constraints`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(async (response) => {
      if (!response.ok) {
        const contentType = response.headers.get('content-type') ?? ''
        const fallbackMessage = 'Unable to save region constraint.'
        if (contentType.includes('application/json')) {
          const errorPayload = (await response.json()) as { detail?: string }
          throw new Error(errorPayload.detail ?? fallbackMessage)
        }
        throw new Error(fallbackMessage)
      }
      return (await response.json()) as RegionConstraint
    })
  },

  deleteRegionConstraint: (token: string, roomId: string, constraintId: string) =>
    request<ApiMessage>(`/rooms/${roomId}/region-constraints/${constraintId}`, {
      method: 'DELETE',
      token,
    }),
}
