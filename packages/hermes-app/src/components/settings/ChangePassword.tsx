import { type FormEvent, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Key } from 'lucide-react'
import { authService } from '@/services/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { ErrorDisplay } from '@/components/ui/error-display'
import { toast } from 'sonner'

export function ChangePassword() {
  const [open, setOpen] = useState(false)
  const [current, setCurrent] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [validation, setValidation] = useState('')
  const change = useMutation({
    mutationFn: () => authService.changePassword(current, password),
    onSuccess: () => {
      close()
      toast.success('Password changed')
    },
  })
  function close() {
    setOpen(false)
    setCurrent('')
    setPassword('')
    setConfirmation('')
    setValidation('')
    change.reset()
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password !== confirmation) {
      setValidation('Passwords must match')
      return
    }
    if (password.length < 8 || new TextEncoder().encode(password).length > 72) {
      setValidation('Use at least 8 characters and at most 72 UTF-8 bytes')
      return
    }
    setValidation('')
    change.mutate()
  }
  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (value) setOpen(true)
        else close()
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Key className="mr-2 h-4 w-4" />
          Change Password
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change password</DialogTitle>
          <DialogDescription>
            Enter your current password and choose a new password.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <Label htmlFor="current-password">Current password</Label>
          <Input
            id="current-password"
            type="password"
            autoComplete="current-password"
            required
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
          <Label htmlFor="new-password">New password</Label>
          <Input
            id="new-password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Label htmlFor="confirm-password">Confirm new password</Label>
          <Input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            required
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
          />
          {(validation || change.error) && (
            <ErrorDisplay
              message={validation || change.error?.message || 'Unable to change password'}
            />
          )}
          <Button type="submit" disabled={change.isPending}>
            Save password
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
