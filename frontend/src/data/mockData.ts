import type {
  AppNavItem,
  DesignVersion,
  NavItem,
  Professional,
  RoomSummary,
} from '../types/app'

export const publicNav: NavItem[] = [
  { label: 'Home', href: '/' },
  { label: 'Features', href: '#features' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Pages', href: '#pages' },
]

export const appNav: AppNavItem[] = [
  { label: 'Dashboard', href: '/app/dashboard', description: 'Project overview' },
  { label: 'AI Design Studio', href: '/app/design-studio', description: 'Upload and design' },
  { label: 'My Home', href: '/app/my-home', description: 'Whole-home consistency' },
  { label: 'Inspiration', href: '/app/inspiration', description: 'Saved references' },
  {
    label: 'Contractor Briefs',
    href: '/app/contractor-briefs',
    description: 'Execution handoff',
  },
  {
    label: 'Professionals',
    href: '/app/professionals',
    description: 'Local directory',
  },
  { label: 'Profile', href: '/app/profile', description: 'Personal details' },
  { label: 'Settings', href: '/app/settings', description: 'Preferences' },
]

export const roomStatuses: RoomSummary[] = [
  { name: 'Master Bedroom', status: 'Designing' },
  { name: 'Living Room', status: 'Completed' },
  { name: 'Kitchen', status: 'Not Started' },
  { name: 'Balcony', status: 'Not Started' },
]

export const recentDesigns = ['Bedroom V3', 'Living Room V2']

export const requirementSections = {
  keep: ['Bed', 'Wardrobe', 'Flooring'],
  remove: ['Old curtains'],
  add: ['Mirror', 'Warm lighting', 'Wall artwork'],
  colours: ['Beige', 'Walnut', 'Cream'],
  avoid: ['Glossy furniture', 'Bright colours'],
}

export const versions: DesignVersion[] = [
  { version: 'V1', label: 'Initial Design', note: 'Base concept created from uploaded room.' },
  { version: 'V2', label: 'Darker Curtains', note: 'Adjusted softness and evening mood.' },
  { version: 'V3', label: 'Mirror Added', note: 'Improved light reflection and utility.' },
  { version: 'V4', label: 'Luxury Version', note: 'Refined styling with richer materials.' },
]

export const professionals: Professional[] = [
  {
    name: 'Rahul Sharma',
    profession: 'Interior Designer',
    area: 'Vijay Nagar, Indore',
    experience: '6 Years',
    rating: '4.5',
  },
  {
    name: 'Neha Jain',
    profession: 'Interior Designer',
    area: 'Palasia, Indore',
    experience: '4 Years',
    rating: '4.3',
  },
  {
    name: 'Amit Verma',
    profession: 'Carpenter',
    area: 'Scheme 78, Indore',
    experience: '8 Years',
    rating: '4.7',
  },
]
