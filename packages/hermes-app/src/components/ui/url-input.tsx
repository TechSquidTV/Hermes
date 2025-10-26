import { useState, useRef, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Link, Upload, Check, AlertCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { isValidUrl } from '@/lib/utils'
import { toast } from 'sonner'

interface UrlInputProps {
  value?: string
  onChange?: (value: string) => void
  onSubmit?: (url: string) => void
  placeholder?: string
  className?: string
  size?: 'sm' | 'default' | 'lg'
  showValidation?: boolean
  disabled?: boolean
  autoFocus?: boolean
}

export function UrlInput({
  value: externalValue,
  onChange,
  onSubmit,
  placeholder = 'Paste video URL here...',
  className,
  size = 'default',
  showValidation = true,
  disabled = false,
  autoFocus = false,
}: UrlInputProps) {
  const [internalValue, setInternalValue] = useState('')
  const [isDragOver, setIsDragOver] = useState(false)
  const [isValid, setIsValid] = useState<boolean | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const value = externalValue !== undefined ? externalValue : internalValue
  const isControlled = externalValue !== undefined

  const validateUrl = useCallback((url: string) => {
    if (!url.trim()) {
      setIsValid(null)
      return
    }
    const valid = isValidUrl(url.trim())
    setIsValid(valid)
    return valid
  }, [])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value

    if (isControlled) {
      onChange?.(newValue)
    } else {
      setInternalValue(newValue)
    }

    if (showValidation) {
      validateUrl(newValue)
    }
  }, [isControlled, onChange, showValidation, validateUrl])

  const handleSubmit = useCallback((e?: React.FormEvent) => {
    e?.preventDefault()

    const url = value.trim()
    if (!url) return

    if (showValidation && !isValidUrl(url)) {
      toast.error('Please enter a valid URL')
      return
    }

    onSubmit?.(url)
  }, [value, onSubmit, showValidation])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }, [handleSubmit])

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)

    const text = e.dataTransfer.getData('text/plain')
    if (text && isValidUrl(text.trim())) {
      const url = text.trim()
      if (isControlled) {
        onChange?.(url)
      } else {
        setInternalValue(url)
      }
      validateUrl(url)
      toast.success('URL detected and added!')
    } else {
      toast.error('Please drop a valid URL')
    }
  }, [isControlled, onChange, validateUrl])

  // Paste handler
  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData.items)
    const textItem = items.find(item => item.type === 'text/plain')

    if (textItem) {
      textItem.getAsString((text) => {
        const url = text.trim()
        if (url && isValidUrl(url)) {
          if (isControlled) {
            onChange?.(url)
          } else {
            setInternalValue(url)
          }
          validateUrl(url)
          toast.success('URL pasted successfully!')
        }
      })
    }
  }, [isControlled, onChange, validateUrl])

  const sizeClasses = {
    sm: 'h-8 text-sm',
    default: 'h-10',
    lg: 'h-12 text-base',
  }

  return (
    <div className={className}>
      <Card className={cn(
        'transition-all duration-200 border-2 border-dashed',
        isDragOver
          ? 'border-primary bg-primary/5 scale-[1.02]'
          : 'border-muted-foreground/25 hover:border-muted-foreground/50',
        showValidation && isValid === false && 'border-destructive bg-destructive/5',
        showValidation && isValid === true && 'border-green-500 bg-green-50/50 dark:bg-green-950/20'
      )}>
        <CardContent className="p-4">
          <div className="space-y-3">
            <div
              className="relative"
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
                {showValidation && isValid === true && (
                  <Check className="h-4 w-4 text-green-500" />
                )}
                {showValidation && isValid === false && (
                  <AlertCircle className="h-4 w-4 text-destructive" />
                )}
                <Upload className={cn(
                  'text-muted-foreground',
                  size === 'sm' && 'h-3 w-3',
                  size === 'default' && 'h-4 w-4',
                  size === 'lg' && 'h-5 w-5'
                )} />
                <Link className={cn(
                  'text-muted-foreground',
                  size === 'sm' && 'h-3 w-3',
                  size === 'default' && 'h-4 w-4',
                  size === 'lg' && 'h-5 w-5'
                )} />
              </div>

              <Input
                ref={inputRef}
                type="url"
                placeholder={placeholder}
                value={value}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                disabled={disabled}
                autoFocus={autoFocus}
                className={cn(
                  'pl-12 pr-12',
                  sizeClasses[size],
                  showValidation && isValid === false && 'border-destructive focus:border-destructive',
                  showValidation && isValid === true && 'border-green-500 focus:border-green-500'
                )}
              />

              {value && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1">
                  {showValidation && isValid === true && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handleSubmit}
                      className={cn(
                        'h-6 px-2',
                        size === 'lg' && 'h-8 px-3'
                      )}
                    >
                      <Check className={cn(
                        'h-3 w-3',
                        size === 'lg' && 'h-4 w-4'
                      )} />
                    </Button>
                  )}
                </div>
              )}
            </div>

            {/* Helper text */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                {showValidation && isValid === true && '✓ Valid URL detected'}
                {showValidation && isValid === false && '✗ Please enter a valid URL'}
                {!showValidation && 'Supports YouTube, Vimeo, and many other platforms'}
              </span>
              <div className="flex items-center gap-1">
                <span>Drag & drop or paste</span>
                {autoFocus && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-5 px-1 text-xs"
                    onClick={() => inputRef.current?.focus()}
                  >
                    Focus
                  </Button>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


