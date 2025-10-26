// Theme System Manifest
// This file exports metadata about all available themes

export interface ThemeMetadata {
  id: string
  name: string
  description: string
  author?: string
  preview: {
    primary: string
    background: string
    accent: string
  }
}

export const themes: ThemeMetadata[] = [
  {
    id: 'hermes',
    name: 'Hermes',
    description: 'Default theme with warm orange accents',
    author: 'Hermes Team',
    preview: {
      primary: 'hsl(28, 60%, 52%)',
      background: 'hsl(0, 0%, 7%)',
      accent: 'hsl(28, 60%, 52%)',
    },
  },
  {
    id: 'nord',
    name: 'Nord',
    description: 'Arctic-inspired cool color palette with blues and greens',
    author: 'Arctic Ice Studio',
    preview: {
      primary: 'hsl(210, 34%, 63%)',
      background: 'hsl(220, 16%, 22%)',
      accent: 'hsl(179, 25%, 65%)',
    },
  },
  {
    id: 'dracula',
    name: 'Dracula',
    description: 'Dark theme with vibrant purples and cyans',
    author: 'Dracula Theme',
    preview: {
      primary: 'hsl(326, 100%, 74%)',
      background: 'hsl(231, 15%, 18%)',
      accent: 'hsl(191, 97%, 77%)',
    },
  },
  {
    id: 'tokyo-night',
    name: 'Tokyo Night',
    description: 'Deep purples and blues inspired by Tokyo at night',
    author: 'Tokyo Night',
    preview: {
      primary: 'hsl(250, 60%, 75%)',
      background: 'hsl(224, 20%, 15%)',
      accent: 'hsl(210, 100%, 70%)',
    },
  },
  {
    id: 'catppuccin',
    name: 'Catppuccin',
    description: 'Pastel color palette with smooth gradients',
    author: 'Catppuccin',
    preview: {
      primary: 'hsl(267, 84%, 81%)',
      background: 'hsl(240, 21%, 15%)',
      accent: 'hsl(189, 71%, 73%)',
    },
  },
]

export const defaultTheme = 'hermes'

// Helper to get theme metadata by ID
export function getTheme(id: string): ThemeMetadata | undefined {
  return themes.find((theme) => theme.id === id)
}

// Helper to validate if a theme exists
export function isValidTheme(id: string): boolean {
  return themes.some((theme) => theme.id === id)
}

