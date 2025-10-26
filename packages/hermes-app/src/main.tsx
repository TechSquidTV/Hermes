import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { AuthProvider } from '@/contexts/AuthContext'
import { Toaster } from '@/components/ui/sonner'
import { queryClient } from '@/lib/queryClient'
import type { AuthContextType } from '@/types/auth'
import './style.css'

// Import generated route tree
import { routeTree } from './routeTree.gen'

// Create router instance
const router = createRouter({
  routeTree,
  context: {
    auth: undefined! as AuthContextType, // This will be provided by AuthProvider
  },
})

// Register router for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)
