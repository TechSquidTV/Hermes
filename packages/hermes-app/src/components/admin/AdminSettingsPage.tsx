import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Settings, UserPlus, Info } from 'lucide-react'
import { toast } from 'sonner'
import { useSystemSettings, useUpdateSignupSetting } from '@/hooks/useSystemSettings'
import { formatDistanceToNow } from 'date-fns'

export function AdminSettingsPage() {
  const { data: settings, isLoading } = useSystemSettings()
  const updateSignup = useUpdateSignupSetting()

  const handleSignupToggle = async (enabled: boolean) => {
    try {
      await updateSignup.mutateAsync(enabled)
      toast.success(
        enabled ? 'Public signups enabled' : 'Public signups disabled',
        {
          description: enabled
            ? 'New users can now register for accounts'
            : 'Only admins can create new accounts',
        }
      )
    } catch (error) {
      toast.error('Failed to update signup setting', {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Settings className="size-8" />
            System Settings
          </h1>
          <p className="text-muted-foreground mt-2">
            Configure system-wide settings and preferences
          </p>
        </div>
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Settings className="size-8" />
          System Settings
        </h1>
        <p className="text-muted-foreground mt-2">
          Configure system-wide settings and preferences
        </p>
      </div>

      <div className="space-y-6">
        {/* User Registration Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserPlus className="size-5" />
              User Registration
            </CardTitle>
            <CardDescription>
              Control how new users can register for accounts
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="allow-signup" className="text-base font-medium">
                  Allow Public Signups
                </Label>
                <p className="text-sm text-muted-foreground">
                  When disabled, only administrators can create new user accounts
                </p>
              </div>
              <Switch
                id="allow-signup"
                checked={settings?.allowPublicSignup ?? false}
                onCheckedChange={handleSignupToggle}
                disabled={updateSignup.isPending}
              />
            </div>

            {/* Info Box */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950">
              <div className="flex gap-3">
                <Info className="size-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                    First User Exception
                  </p>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    The first user signup is always allowed regardless of this setting to ensure system bootstrap capability.
                  </p>
                </div>
              </div>
            </div>

            {/* Last Updated Info */}
            {settings?.updatedAt && (
              <div className="text-xs text-muted-foreground border-t pt-4">
                Last updated {formatDistanceToNow(new Date(settings.updatedAt), { addSuffix: true })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Future Settings Placeholder */}
        <Card className="border-dashed">
          <CardHeader>
            <CardTitle className="text-muted-foreground">Additional Settings</CardTitle>
            <CardDescription>
              More system configuration options will be available here in future releases
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  )
}

