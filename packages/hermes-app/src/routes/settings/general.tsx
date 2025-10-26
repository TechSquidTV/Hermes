import { createFileRoute } from '@tanstack/react-router'
import { GeneralSettings } from '@/components/settings/GeneralSettings'

export const Route = createFileRoute('/settings/general')({
  component: GeneralSettings,
})

