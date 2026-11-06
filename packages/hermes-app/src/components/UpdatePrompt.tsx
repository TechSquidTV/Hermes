import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'

export function UpdatePrompt() {
  const [available, setAvailable] = useState(false)

  useEffect(() => {
    if (import.meta.env.DEV) return
    let controller: AbortController | null = null
    let disposed = false
    const check = async () => {
      if (document.visibilityState === 'hidden' || controller) return
      controller = new AbortController()
      const timeout = window.setTimeout(() => controller?.abort(), 5_000)
      try {
        const response = await fetch(`${import.meta.env.BASE_URL}build-id.txt`, {
          cache: 'no-store',
          signal: controller.signal
        })
        if (!response.ok) return
        const build = (await response.text()).trim()
        if (!disposed && /^[0-9a-f-]{36}$/.test(build) && build !== __HERMES_BUILD_ID__) {
          setAvailable(true)
        }
      } catch {
        // Deployment and network outages are temporary; retry on the next check.
      } finally {
        window.clearTimeout(timeout)
        controller = null
      }
    }
    void check()
    const interval = window.setInterval(() => void check(), 60_000)
    const onFocus = () => void check()
    window.addEventListener('focus', onFocus)
    document.addEventListener('visibilitychange', onFocus)
    return () => {
      disposed = true
      window.clearInterval(interval)
      controller?.abort()
      window.removeEventListener('focus', onFocus)
      document.removeEventListener('visibilitychange', onFocus)
    }
  }, [])

  if (!available) return null
  return (
    <aside aria-label="Application update" className="fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-3 rounded-lg border bg-background p-4 text-foreground shadow-lg" role="status">
      <p>A new version of Hermes is ready.</p>
      <p className="text-sm text-muted-foreground">Save any changes, then reload to finish updating.</p>
      <Button onClick={() => window.location.reload()}>Reload</Button>
    </aside>
  )
}
