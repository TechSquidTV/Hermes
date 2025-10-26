import * as React from "react"
import { Link as RouterLink, type LinkProps as RouterLinkProps } from '@tanstack/react-router'
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const linkVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "text-foreground hover:text-foreground/80",
        destructive: "text-destructive hover:text-destructive/80",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface LinkProps
  extends RouterLinkProps,
    VariantProps<typeof linkVariants> {
  className?: string
}

const Link = React.forwardRef<HTMLAnchorElement, LinkProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <RouterLink
        className={cn(linkVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    )
  }
)
Link.displayName = "Link"

export { Link }
