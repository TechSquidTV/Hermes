import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Users,
  Plus,
  Trash2,
  Shield,
  ShieldOff,
  UserCheck,
  UserX,
  Mail,
  User as UserIcon
} from 'lucide-react'
import { toast } from 'sonner'
import { adminService, type CreateUserRequest } from '@/services/admin'
import type { User } from '@/types/auth'
import { useAuth } from '@/contexts/AuthContext'

export function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newUser, setNewUser] = useState<CreateUserRequest>({
    username: '',
    email: '',
    password: '',
    isAdmin: false,
  })
  const { user: currentUser } = useAuth()

  const loadUsers = async () => {
    try {
      setLoading(true)
      const data = await adminService.listUsers()
      setUsers(data)
    } catch (error) {
      toast.error('Failed to load users', {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleCreateUser = async () => {
    if (!newUser.username.trim() || !newUser.email.trim() || !newUser.password.trim()) {
      toast.error('Please fill in all fields')
      return
    }

    try {
      await adminService.createUser(newUser)
      toast.success('User created successfully')
      setNewUser({ username: '', email: '', password: '', isAdmin: false })
      setShowCreateForm(false)
      loadUsers()
    } catch (error) {
      toast.error('Failed to create user', {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  const handleToggleAdmin = async (userId: string, username: string, isCurrentlyAdmin: boolean) => {
    const action = isCurrentlyAdmin ? 'demote' : 'promote'
    if (!confirm(`Are you sure you want to ${action} ${username} ${isCurrentlyAdmin ? 'from' : 'to'} admin?`)) {
      return
    }

    try {
      await adminService.updateAdminStatus(userId, !isCurrentlyAdmin)
      toast.success(`User ${action}d successfully`)
      loadUsers()
    } catch (error) {
      toast.error(`Failed to ${action} user`, {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  const handleToggleActive = async (userId: string, username: string, isCurrentlyActive: boolean) => {
    const action = isCurrentlyActive ? 'deactivate' : 'activate'
    if (!confirm(`Are you sure you want to ${action} ${username}?`)) {
      return
    }

    try {
      await adminService.updateActiveStatus(userId, !isCurrentlyActive)
      toast.success(`User ${action}d successfully`)
      loadUsers()
    } catch (error) {
      toast.error(`Failed to ${action} user`, {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  const handleDeleteUser = async (userId: string, username: string) => {
    if (!confirm(`Are you sure you want to delete ${username}? This action cannot be undone.`)) {
      return
    }

    try {
      await adminService.deleteUser(userId)
      toast.success('User deleted successfully')
      loadUsers()
    } catch (error) {
      toast.error('Failed to delete user', {
        description: error instanceof Error ? error.message : 'Unknown error',
      })
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Users className="h-8 w-8" />
          User Management
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage user accounts, permissions, and access
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              All Users ({users.length})
            </CardTitle>
            <Button onClick={() => setShowCreateForm(!showCreateForm)}>
              <Plus className="h-4 w-4 mr-2" />
              Create User
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {showCreateForm && (
            <Card className="bg-muted/50">
              <CardContent className="pt-6 space-y-4">
                <h3 className="font-semibold">Create New User</h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <Label htmlFor="username">Username</Label>
                    <Input
                      id="username"
                      value={newUser.username}
                      onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                      placeholder="johndoe"
                    />
                  </div>
                  <div>
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={newUser.email}
                      onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                      placeholder="john@example.com"
                    />
                  </div>
                  <div>
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      value={newUser.password}
                      onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                      placeholder="••••••••"
                    />
                  </div>
                  <div className="flex items-center gap-2 pt-6">
                    <input
                      id="isAdmin"
                      type="checkbox"
                      checked={newUser.isAdmin}
                      onChange={(e) => setNewUser({ ...newUser, isAdmin: e.target.checked })}
                      className="h-4 w-4"
                    />
                    <Label htmlFor="isAdmin" className="cursor-pointer">
                      Grant admin privileges
                    </Label>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleCreateUser}>
                    Create User
                  </Button>
                  <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                    Cancel
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading users...
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No users found
            </div>
          ) : (
            <div className="space-y-2">
              {users.map((user) => (
                <Card key={user.id} className="p-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <UserIcon className="h-4 w-4 text-muted-foreground" />
                        <span className="font-semibold">{user.username}</span>
                        {user.isAdmin && (
                          <Badge variant="default" className="text-xs">
                            <Shield className="h-3 w-3 mr-1" />
                            Admin
                          </Badge>
                        )}
                        {!user.isActive && (
                          <Badge variant="destructive" className="text-xs">
                            Inactive
                          </Badge>
                        )}
                        {currentUser?.id === user.id && (
                          <Badge variant="secondary" className="text-xs">
                            You
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Mail className="h-3 w-3" />
                        {user.email}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleAdmin(user.id, user.username, user.isAdmin)}
                        disabled={currentUser?.id === user.id}
                        title={currentUser?.id === user.id ? "Cannot modify your own admin status" : undefined}
                      >
                        {user.isAdmin ? (
                          <>
                            <ShieldOff className="h-3 w-3 mr-1" />
                            Demote
                          </>
                        ) : (
                          <>
                            <Shield className="h-3 w-3 mr-1" />
                            Promote
                          </>
                        )}
                      </Button>

                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleActive(user.id, user.username, user.isActive)}
                        disabled={currentUser?.id === user.id}
                        title={currentUser?.id === user.id ? "Cannot deactivate yourself" : undefined}
                      >
                        {user.isActive ? (
                          <>
                            <UserX className="h-3 w-3 mr-1" />
                            Deactivate
                          </>
                        ) : (
                          <>
                            <UserCheck className="h-3 w-3 mr-1" />
                            Activate
                          </>
                        )}
                      </Button>

                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleDeleteUser(user.id, user.username)}
                        disabled={currentUser?.id === user.id}
                        title={currentUser?.id === user.id ? "Cannot delete yourself" : undefined}
                      >
                        <Trash2 className="h-3 w-3 mr-1" />
                        Delete
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
