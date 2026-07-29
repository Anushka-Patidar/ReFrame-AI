export type SessionUser = {
  id: string
  name: string
  email: string
  phone: string
  city: string
  created_at: string
}

export type TokenResponse = {
  access_token: string
  token_type: string
  user: SessionUser
}

export type DashboardSummary = {
  greeting: string
  summary: string
  average_design_score: number
  estimated_budget: number
  my_home: Array<{ name: string; status: string }>
  recent_designs: string[]
  quick_actions: string[]
}

export type OverallStyleProfile = {
  style: string
  colours: string[]
  lighting: string
  wood: string
  metal_finish: string
}

export type HomeProfile = {
  id: string
  user_id: string
  property_type: string
  rooms: number
  preferred_style: string
  overall_style_profile: OverallStyleProfile
}

export type RoomDimensions = {
  length: number
  width: number
  height: number
}

export type Room = {
  id: string
  user_id: string
  room_type: string
  dimensions: RoomDimensions
  status: string
  original_image_url?: string | null
  match_home_style: boolean
  created_at: string
}

export type ChatMessage = {
  role: string
  content: string
}

export type DesignRequirements = {
  room: string
  style: string
  budget: number
  keep: string[]
  remove: string[]
  add: string[]
  colours: string[]
  avoid: string[]
  notes: string[]
}

export type RegionAction = 'KEEP' | 'CHANGE' | 'REMOVE'

export type RegionConstraint = {
  id: string
  action: RegionAction
  label: string
  mask_url: string
  image_width: number
  image_height: number
  created_at: string
}

export type SpaceCheck = {
  room_size: string
  checks: Array<{ item: string; status: string; note: string }>
  recommendation: string
}

export type DesignVersion = {
  id: string
  room_id: string
  version: string
  title: string
  note: string
  image_url?: string | null
  engine?: string | null
  is_finalized: boolean
  created_at: string
}

export type AiCapabilities = {
  photoreal_image_edit: boolean
  claude_chat: boolean
  openai_chat: boolean
  local_style_grade: boolean
  openai_image_model: string
  recommended_setup: string
  mode?: 'photoreal' | 'local-grade'
  image_provider?: string
  pollinations_enabled?: boolean
  gemini_enabled?: boolean
  supports_reference_image_edit?: boolean
  local_ai_profile?: string | null
  generation_busy?: boolean
}

export type DesignScore = {
  id: string
  design_version_id: string
  total_score: number
  categories: Record<string, number>
  observation: string
  recommendation: string
}

export type ContractorBrief = {
  id: string
  room_id: string
  design_version_id: string
  room_name: string
  style: string
  budget: number
  room_size: string
  keep_existing: string[]
  remove: string[]
  wall: string
  lighting: string[]
  additions: string[]
  colour_palette: string[]
  important_notes: string[]
}

export type Inspiration = {
  id: string
  user_id: string
  image_url: string
  detected_tags: string[]
}

export type Professional = {
  id: string
  name: string
  profession: string
  city: string
  area: string
  phone: string
  experience_years: number
  rating: number
  availability: string
}

export type ApiMessage = {
  message: string
  timestamp: string
}
