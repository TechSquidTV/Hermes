import { AppSidebar } from "./AppSidebar"
import { Link, useLocation } from "@tanstack/react-router"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { Separator } from "@/components/ui/separator"
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/animate-ui/components/radix/sidebar"

interface AppLayoutProps {
  children: React.ReactNode
}

// Route name mappings for better readability
const routeNames: Record<string, string> = {
  '/': 'Dashboard',
  '/queue': 'Queue',
  '/settings': 'Settings',
  '/settings/general': 'General',
  '/settings/polling': 'Polling',
  '/settings/api-keys': 'API Keys',
  '/settings/appearance': 'Appearance',
  '/auth/login': 'Login',
  '/auth/signup': 'Sign Up',
}

function DynamicBreadcrumbs() {
  const location = useLocation()
  const pathname = location.pathname
  
  // Build breadcrumb segments from the pathname
  const pathSegments = pathname.split('/').filter(Boolean)
  
  // If we're at the root, just show Dashboard
  if (pathname === '/') {
    return (
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem className="hidden md:block">
            <BreadcrumbLink asChild>
              <Link to="/">Hermes</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator className="hidden md:block" />
          <BreadcrumbItem>
            <BreadcrumbPage>Dashboard</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    )
  }
  
  // Build the breadcrumb trail
  const breadcrumbs: { path: string; label: string; isLast: boolean }[] = []
  let currentPath = ''
  
  pathSegments.forEach((segment, index) => {
    currentPath += `/${segment}`
    const label = routeNames[currentPath] || segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ')
    const isLast = index === pathSegments.length - 1
    
    breadcrumbs.push({
      path: currentPath,
      label,
      isLast,
    })
  })
  
  return (
    <Breadcrumb>
      <BreadcrumbList>
        <BreadcrumbItem className="hidden md:block">
          <BreadcrumbLink asChild>
            <Link to="/">Hermes</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        <BreadcrumbSeparator className="hidden md:block" />
        {breadcrumbs.map((crumb) => (
          <span key={crumb.path} className="contents">
            <BreadcrumbItem>
              {crumb.isLast ? (
                <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
              ) : (
                <BreadcrumbLink asChild>
                  <Link to={crumb.path}>{crumb.label}</Link>
                </BreadcrumbLink>
              )}
            </BreadcrumbItem>
            {!crumb.isLast && <BreadcrumbSeparator className="hidden md:block" />}
          </span>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <>
      <div className="grain-overlay"></div>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background/80 backdrop-blur-md px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
            <DynamicBreadcrumbs />
          </header>
          <div className="flex flex-1 flex-col gap-4 p-4">
            {children}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </>
  )
}
