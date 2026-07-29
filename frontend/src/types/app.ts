export type RoomStatus = 'Completed' | 'Designing' | 'Not Started'

export type NavItem = {
  label: string
  href: string
}

export type AppNavItem = NavItem & {
  description: string
}

export type RoomSummary = {
  name: string
  status: RoomStatus
}

export type DesignVersion = {
  version: string
  label: string
  note: string
}

export type Professional = {
  name: string
  profession: string
  area: string
  experience: string
  rating: string
}
