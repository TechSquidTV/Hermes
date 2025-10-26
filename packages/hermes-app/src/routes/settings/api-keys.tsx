import { createFileRoute } from '@tanstack/react-router'
import { ApiKeySettings } from '@/components/settings/ApiKeySettings'

export const Route = createFileRoute('/settings/api-keys')({
  component: ApiKeySettings,
})

