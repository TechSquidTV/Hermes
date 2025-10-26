import { useState, useRef, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Search, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SearchInputProps {
  placeholder?: string
  value?: string
  onChange?: (value: string) => void
  onClear?: () => void
  className?: string
  size?: 'sm' | 'default' | 'lg'
  showClearButton?: boolean
  autoFocus?: boolean
}

export function SearchInput({
  placeholder = 'Search...',
  value: externalValue,
  onChange,
  onClear,
  className,
  size = 'default',
  showClearButton = true,
  autoFocus = false,
}: SearchInputProps) {
  const [internalValue, setInternalValue] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Use external value if provided, otherwise use internal state
  const value = externalValue !== undefined ? externalValue : internalValue
  const isControlled = externalValue !== undefined

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value

    if (isControlled) {
      onChange?.(newValue)
    } else {
      setInternalValue(newValue)
    }
  }

  const handleClear = () => {
    if (isControlled) {
      onChange?.('')
      onClear?.()
    } else {
      setInternalValue('')
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      handleClear()
    }
  }

  // Auto-focus functionality
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])

  const sizeClasses = {
    sm: 'h-8 pl-8 pr-8',
    default: 'h-10 pl-10 pr-10',
    lg: 'h-12 pl-12 pr-12 text-base',
  }

  const iconSizes = {
    sm: 'h-3 w-3',
    default: 'h-4 w-4',
    lg: 'h-5 w-5',
  }

  return (
    <div className={cn('relative', className)}>
      <Search className={cn(
        'absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground',
        iconSizes[size]
      )} />
      <Input
        ref={inputRef}
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        className={cn(
          'pl-10',
          showClearButton && value && 'pr-10',
          sizeClasses[size]
        )}
      />
      {showClearButton && value && (
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={cn(
            'absolute right-1 top-1/2 transform -translate-y-1/2 h-8 w-8',
            size === 'lg' && 'h-10 w-10',
            size === 'sm' && 'h-6 w-6'
          )}
          onClick={handleClear}
        >
          <X className={iconSizes[size]} />
        </Button>
      )}
    </div>
  )
}


