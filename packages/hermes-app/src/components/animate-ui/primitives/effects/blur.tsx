'use client'

import React from 'react'
import { motion, useInView, type HTMLMotionProps } from 'framer-motion'

export interface BlurProps extends Omit<HTMLMotionProps<'div'>, 'initial' | 'animate'> {
  /**
   * Animate the element when it is in view
   * @default false
   */
  inView?: boolean
  /**
   * Animate the element only once when it is in view
   * @default true
   */
  inViewOnce?: boolean
  /**
   * The margin of the element to be in view
   * @default "0px"
   */
  inViewMargin?: string | number
  /**
   * The delay of the animation
   * @default 0
   */
  delay?: number
  /**
   * The blur of the blur
   * @default 0
   */
  blur?: number
  /**
   * The initial blur of the blur
   * @default 10
   */
  initialBlur?: number
}

export function Blur({
  children,
  inView = false,
  inViewOnce = true,
  inViewMargin = '0px',
  delay = 0,
  blur = 0,
  initialBlur = 10,
  className,
  ...props
}: BlurProps) {
  const ref = React.useRef(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const isInView = useInView(ref, { once: inViewOnce, margin: inViewMargin as any })

  const shouldAnimate = inView ? isInView : true

  return (
    <motion.div
      ref={ref}
      initial={{
        filter: `blur(${initialBlur}px)`,
        opacity: 0,
      }}
      animate={
        shouldAnimate
          ? {
              filter: `blur(${blur}px)`,
              opacity: 1,
            }
          : undefined
      }
      transition={{
        delay,
        duration: 0.4,
        ease: 'easeOut',
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export interface BlursProps extends BlurProps {
  /**
   * The children of the blurs
   */
  children: React.ReactElement | React.ReactElement[]
  /**
   * The delay between each blur
   * @default 0
   */
  holdDelay?: number
}

export function Blurs({ children, holdDelay = 0, ...props }: BlursProps) {
  const childrenArray = React.Children.toArray(children) as React.ReactElement[]

  return (
    <>
      {childrenArray.map((child, index) => (
        <Blur key={index} delay={index * holdDelay} {...props}>
          {child}
        </Blur>
      ))}
    </>
  )
}

