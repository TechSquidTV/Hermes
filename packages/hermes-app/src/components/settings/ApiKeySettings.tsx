import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Key, Plus, Copy, Trash2, Clock, Eye, Shield } from 'lucide-react'
import { toast } from 'sonner'
import { useApiKeys } from '@/hooks/useApiKeys'
import { TokenStorage } from '@/utils/tokenStorage'

export function ApiKeySettings() {
  const { keys, createKey, revokeKey } = useApiKeys()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyPermissions, setNewKeyPermissions] = useState<string[]>([])


  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key')
      return
    }

    try {
      const result = await createKey.mutateAsync({
        name: newKeyName.trim(),
        permissions: newKeyPermissions,
      })

      // Show the new key to the user (only time they'll see it)
      toast.success(
        <div className="space-y-2">
          <div>API key created successfully!</div>
          <div className="font-mono text-sm bg-muted p-2 rounded border">
            {result.key}
          </div>
          <div className="text-xs text-muted-foreground">
            Copy this key now - you won&apos;t be able to see it again!
          </div>
        </div>,
        { duration: 10000 }
      )

      // Reset form
      setNewKeyName('')
      setNewKeyPermissions([])
      setShowCreateForm(false)
    } catch (_error) {
      // Error handling is done in the hook
    }
  }

  const handleRevokeKey = async (keyId: string, keyName: string) => {
    if (confirm(`Are you sure you want to revoke the API key "${keyName}"? This action cannot be undone.`)) {
      try {
        await revokeKey.mutateAsync(keyId)
      } catch (_error) {
        // Error handling is done in the hook
      }
    }
  }

  const togglePermission = (permission: string) => {
    setNewKeyPermissions(prev =>
      prev.includes(permission)
        ? prev.filter(p => p !== permission)
        : [...prev, permission]
    )
  }

  const handleCopyJWTToken = () => {
    const token = TokenStorage.getAccessToken()
    if (token) {
      navigator.clipboard.writeText(token)
      toast.success('JWT token copied to clipboard!')
    } else {
      toast.error('No JWT token available. Please log in again.')
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            API Keys
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Generate API keys for external applications (Sonarr, Radarr, mobile apps, etc.)
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="w-full sm:w-auto"
            disabled={createKey.isPending}
          >
            <Plus className="h-4 w-4 mr-2" />
            Generate New Key
          </Button>

          {/* Create API Key Form */}
          {showCreateForm && (
            <Card className="border-dashed">
              <CardHeader>
                <CardTitle className="text-lg">Create New API Key</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="key-name">Key Name</Label>
                  <Input
                    id="key-name"
                    placeholder="e.g., Sonarr Integration"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Permissions</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {['read', 'write', 'download', 'delete'].map((permission) => (
                      <Button
                        key={permission}
                        type="button"
                        variant={newKeyPermissions.includes(permission) ? "default" : "outline"}
                        size="sm"
                        onClick={() => togglePermission(permission)}
                        className="justify-start"
                      >
                        {permission}
                      </Button>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={handleCreateKey}
                    disabled={createKey.isPending}
                    size="sm"
                  >
                    {createKey.isPending ? 'Creating...' : 'Create Key'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setShowCreateForm(false)}
                    size="sm"
                  >
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* API Keys List */}
          <div className="space-y-3">
            {keys.isLoading ? (
              <div className="text-center py-8 text-muted-foreground">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-2"></div>
                <p className="text-sm">Loading API keys...</p>
              </div>
            ) : keys.data && keys.data.length > 0 ? (
              keys.data.map((apiKey) => (
                <div
                  key={apiKey.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border rounded-lg gap-3"
                >
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <h4 className="font-medium">{apiKey.name}</h4>
                      <Badge variant={apiKey.isActive ? "default" : "secondary"}>
                        {apiKey.isActive ? 'Active' : 'Inactive'}
                      </Badge>
                      <Badge variant="outline">
                        {apiKey.permissions.join(', ') || 'No permissions'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Created: {new Date(apiKey.createdAt).toLocaleDateString()}
                      </div>
                      {apiKey.lastUsed && (
                        <div className="flex items-center gap-1">
                          <Eye className="h-3 w-3" />
                          Last used: {new Date(apiKey.lastUsed).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => navigator.clipboard.writeText(`Key ID: ${apiKey.id}`)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleRevokeKey(apiKey.id, apiKey.name)}
                      disabled={revokeKey.isPending}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Key className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="text-sm">No API keys generated yet</p>
                <p className="text-xs">Create your first API key to get started</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* JWT Token Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Current JWT Token
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Your JWT token can be used as an API key for authentication
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1">
                <p className="text-sm font-medium mb-1">Access Token</p>
                <code className="text-xs text-muted-foreground break-all">
                  {TokenStorage.getAccessToken()
                    ? `${TokenStorage.getAccessToken()!.substring(0, 50)}...`
                    : 'No active token'
                  }
                </code>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyJWTToken}
                disabled={!TokenStorage.getAccessToken()}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="text-xs text-muted-foreground space-y-1">
            <p><strong>How to use:</strong> Include this token in the Authorization header as <code>Bearer &lt;token&gt;</code></p>
            <p><strong>Expires:</strong> Every 15 minutes (auto-refreshes)</p>
            <p><strong>Alternative:</strong> Create dedicated API keys above for long-term access</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


