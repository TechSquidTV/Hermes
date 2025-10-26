import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Palette, Sun, Moon, Monitor } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { Badge } from '@/components/ui/badge'

export function AppearanceSettings() {
  const { 
    theme, 
    mode, 
    effectiveMode, 
    setTheme, 
    setMode, 
    availableThemes, 
    isLoading 
  } = useTheme()

  return (
    <div className="space-y-6">
      {/* Theme Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5" />
            Color Theme
          </CardTitle>
          <CardDescription>
            Choose your preferred color scheme from our curated collection
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="theme-select">Theme</Label>
            <Select value={theme} onValueChange={setTheme} disabled={isLoading}>
              <SelectTrigger id="theme-select" className="w-full">
                <SelectValue placeholder="Select a theme" />
              </SelectTrigger>
              <SelectContent>
                {availableThemes.map((t) => (
                  <SelectItem key={t.id} value={t.id}>
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div 
                          className="h-4 w-4 rounded-sm border" 
                          style={{ background: t.preview.primary }}
                        />
                        <div 
                          className="h-4 w-4 rounded-sm border" 
                          style={{ background: t.preview.background }}
                        />
                        <div 
                          className="h-4 w-4 rounded-sm border" 
                          style={{ background: t.preview.accent }}
                        />
                      </div>
                      <span>{t.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {theme && (
              <p className="text-sm text-muted-foreground">
                {availableThemes.find(t => t.id === theme)?.description}
              </p>
            )}
          </div>

          {/* Theme Preview */}
          <div className="space-y-2">
            <Label>Preview</Label>
            <div className="grid grid-cols-2 gap-2 p-4 rounded-lg border bg-card">
              <div className="space-y-2">
                <div className="h-8 rounded bg-primary" />
                <div className="h-4 rounded bg-primary/20" />
                <div className="h-4 rounded bg-primary/10" />
              </div>
              <div className="space-y-2">
                <div className="h-8 rounded bg-accent" />
                <div className="h-4 rounded bg-accent/20" />
                <div className="h-4 rounded bg-accent/10" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Mode Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {effectiveMode === 'light' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
            Display Mode
          </CardTitle>
          <CardDescription>
            Choose between light, dark, or system-based appearance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RadioGroup value={mode} onValueChange={(value) => setMode(value as 'light' | 'dark' | 'system')} disabled={isLoading}>
            <div className="flex items-center space-x-2 rounded-lg border p-4 hover:bg-accent/50 transition-colors">
              <RadioGroupItem value="light" id="light" />
              <Label htmlFor="light" className="flex items-center gap-2 cursor-pointer flex-1">
                <Sun className="h-4 w-4" />
                <div className="space-y-1">
                  <div className="font-medium">Light</div>
                  <div className="text-sm text-muted-foreground">Bright and clear interface</div>
                </div>
              </Label>
            </div>

            <div className="flex items-center space-x-2 rounded-lg border p-4 hover:bg-accent/50 transition-colors">
              <RadioGroupItem value="dark" id="dark" />
              <Label htmlFor="dark" className="flex items-center gap-2 cursor-pointer flex-1">
                <Moon className="h-4 w-4" />
                <div className="space-y-1">
                  <div className="font-medium">Dark</div>
                  <div className="text-sm text-muted-foreground">Easy on the eyes in low light</div>
                </div>
              </Label>
            </div>

            <div className="flex items-center space-x-2 rounded-lg border p-4 hover:bg-accent/50 transition-colors">
              <RadioGroupItem value="system" id="system" />
              <Label htmlFor="system" className="flex items-center gap-2 cursor-pointer flex-1">
                <Monitor className="h-4 w-4" />
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="font-medium">System</div>
                    {mode === 'system' && (
                      <Badge variant="secondary" className="text-xs">
                        Using {effectiveMode}
                      </Badge>
                    )}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Adapts to your system preference
                  </div>
                </div>
              </Label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Custom Themes Info */}
      <Card>
        <CardHeader>
          <CardTitle>Custom Themes</CardTitle>
          <CardDescription>
            Want to create your own theme? Check out our theme creation guide
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            You can create custom themes by copying the template file in{' '}
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">src/themes/_template.css</code>.
            See{' '}
            <code className="text-xs bg-muted px-1.5 py-0.5 rounded">src/themes/README.md</code>{' '}
            for detailed instructions.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}

