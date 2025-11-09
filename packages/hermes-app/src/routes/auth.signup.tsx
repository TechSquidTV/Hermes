import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Loader2, Check, X, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { toast } from 'sonner'
import { HermesLogoLight } from '@/components/hermes-logo'
import { configService } from '@/services/config'

function SignupPage() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [signupDisabled, setSignupDisabled] = useState(false)
  const [checkingConfig, setCheckingConfig] = useState(true)
  const { signup } = useAuth()
  const navigate = useNavigate()

  // Check if signup is disabled
  useEffect(() => {
    const checkSignupStatus = async () => {
      try {
        const config = await configService.getPublicConfig()
        setSignupDisabled(!config.allowPublicSignup)
      } catch (error) {
        console.error('[Signup] Failed to fetch public config:', error)
        // On error, assume signup is allowed (fail open for better UX)
        setSignupDisabled(false)
      } finally {
        setCheckingConfig(false)
      }
    }

    checkSignupStatus()
  }, [])

  // Password validation
  const passwordRequirements = {
    minLength: password.length >= 8,
    hasUpperCase: /[A-Z]/.test(password),
    hasLowerCase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
  }

  const isPasswordValid = Object.values(passwordRequirements).every(Boolean)
  const doPasswordsMatch = password === confirmPassword && password.length > 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!isPasswordValid) {
      toast.error('Please meet all password requirements')
      return
    }

    if (!doPasswordsMatch) {
      toast.error('Passwords do not match')
      return
    }

    setIsLoading(true)

    try {
      await signup({ username, email, password })
      toast.success('Account created successfully!')
      navigate({ to: '/' })
    } catch (error) {
      console.error('[Signup] Failed:', error)

      // Handle 403 Forbidden (signup disabled)
      const errorMessage = error instanceof Error ? error.message : String(error)
      if (errorMessage.includes('403')) {
        toast.error('Public signup is disabled. Contact your administrator.')
        setSignupDisabled(true)
      } else if (errorMessage.includes('409')) {
        toast.error('Username or email already exists')
      } else {
        toast.error('Signup failed. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  // Show loading state while checking config
  if (checkingConfig) {
    return (
      <div className="flex items-center justify-center p-4">
        <Card className="w-full max-w-md shadow-lg">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin mb-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="flex aspect-square size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
              <HermesLogoLight className="size-6" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold text-center">Create an account</CardTitle>
          <CardDescription className="text-center">
            Start downloading videos with Hermes
          </CardDescription>
        </CardHeader>
        <CardContent>
          {signupDisabled && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Signup Disabled</AlertTitle>
              <AlertDescription>
                Public account registration is currently disabled. Please contact your administrator to create an account for you.
              </AlertDescription>
            </Alert>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="johndoe"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={isLoading || signupDisabled}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading || signupDisabled}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Create a strong password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading || signupDisabled}
              />
              {password.length > 0 && (
                <div className="space-y-1 text-xs mt-2">
                  <PasswordRequirement
                    met={passwordRequirements.minLength}
                    text="At least 8 characters"
                  />
                  <PasswordRequirement
                    met={passwordRequirements.hasUpperCase}
                    text="One uppercase letter"
                  />
                  <PasswordRequirement
                    met={passwordRequirements.hasLowerCase}
                    text="One lowercase letter"
                  />
                  <PasswordRequirement
                    met={passwordRequirements.hasNumber}
                    text="One number"
                  />
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={isLoading || signupDisabled}
              />
              {confirmPassword.length > 0 && (
                <PasswordRequirement
                  met={doPasswordsMatch}
                  text="Passwords match"
                />
              )}
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || signupDisabled || !isPasswordValid || !doPasswordsMatch}
              size="lg"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create account'
              )}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <div className="relative w-full">
            <div className="absolute inset-0 flex items-center">
              <Separator />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or
              </span>
            </div>
          </div>
          <div className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Button
              variant="link"
              className="px-0 font-normal"
              onClick={() => navigate({ to: '/auth/login' })}
            >
              Sign in
            </Button>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}

function PasswordRequirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div className={`flex items-center gap-2 ${met ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
      {met ? (
        <Check className="h-3 w-3" />
      ) : (
        <X className="h-3 w-3" />
      )}
      <span>{text}</span>
    </div>
  )
}

export const Route = createFileRoute('/auth/signup')({
  component: () => (
    <ProtectedRoute requireAuth={false}>
      <SignupPage />
    </ProtectedRoute>
  ),
})
