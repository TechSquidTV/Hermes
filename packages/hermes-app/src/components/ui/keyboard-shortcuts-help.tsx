import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Keyboard } from 'lucide-react'

interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  metaKey?: boolean
  description: string
}

const shortcuts: KeyboardShortcut[] = [
  {
    key: 'k',
    ctrlKey: true,
    description: 'Focus search input',
  },
  {
    key: 'n',
    ctrlKey: true,
    description: 'Focus URL input (dashboard)',
  },
  {
    key: '/',
    description: 'Focus search input',
  },
  {
    key: 'Escape',
    description: 'Clear focus',
  },
  {
    key: '1',
    altKey: true,
    description: 'Navigate to Dashboard',
  },
  {
    key: '2',
    altKey: true,
    description: 'Navigate to Queue',
  },
  {
    key: '3',
    altKey: true,
    description: 'Navigate to Settings',
  },
]

function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = []

  if (shortcut.ctrlKey || shortcut.metaKey) parts.push('Ctrl')
  if (shortcut.altKey) parts.push('Alt')
  if (shortcut.shiftKey) parts.push('Shift')
  if (shortcut.key) parts.push(shortcut.key.toUpperCase())

  return parts.join(' + ')
}

interface KeyboardShortcutsHelpProps {
  children: React.ReactNode
}

export function KeyboardShortcutsHelp({ children }: KeyboardShortcutsHelpProps) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="h-5 w-5" />
            Keyboard Shortcuts
          </DialogTitle>
          <DialogDescription>
            Use these shortcuts to navigate and control the application faster.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-4">
          {shortcuts.map((shortcut, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-2 rounded-md bg-muted/50"
            >
              <span className="text-sm">{shortcut.description}</span>
              <Badge variant="secondary" className="font-mono">
                {formatShortcut(shortcut)}
              </Badge>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
