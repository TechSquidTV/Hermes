import { useState, useCallback } from 'react'

export type SettingsSection =
  | 'general'
  | 'api-keys'
  | 'connection'
  | 'media'
  | 'storage'
  | 'appearance'
  | 'security'
  | 'advanced'

interface UseSettingsNavigationOptions {
  initialSection?: SettingsSection
  onSectionChange?: (section: SettingsSection) => void
}

export function useSettingsNavigation(options: UseSettingsNavigationOptions = {}) {
  const { initialSection = 'general', onSectionChange } = options
  const [activeSection, setActiveSection] = useState<SettingsSection>(initialSection)

  const navigateToSection = useCallback((section: SettingsSection) => {
    setActiveSection(section)
    onSectionChange?.(section)
  }, [onSectionChange])

  const sections = [
    { id: 'general' as SettingsSection, title: 'General', description: 'Application info and user profile' },
    { id: 'api-keys' as SettingsSection, title: 'API Keys', description: 'Generate keys for external access' },
    { id: 'connection' as SettingsSection, title: 'Connection', description: 'API server and connection settings' },
    { id: 'media' as SettingsSection, title: 'Media', description: 'Download preferences and naming' },
    { id: 'storage' as SettingsSection, title: 'Storage', description: 'Storage management and cleanup' },
    { id: 'appearance' as SettingsSection, title: 'Appearance', description: 'Theme and display settings' },
    { id: 'security' as SettingsSection, title: 'Security', description: 'Authentication and security settings' },
    { id: 'advanced' as SettingsSection, title: 'Advanced', description: 'Backup, restore, and debugging' },
  ]

  return {
    activeSection,
    setActiveSection: navigateToSection,
    sections,
    isGeneral: activeSection === 'general',
    isApiKeys: activeSection === 'api-keys',
    isConnection: activeSection === 'connection',
    isMedia: activeSection === 'media',
    isStorage: activeSection === 'storage',
    isAppearance: activeSection === 'appearance',
    isSecurity: activeSection === 'security',
    isAdvanced: activeSection === 'advanced',
  }
}


