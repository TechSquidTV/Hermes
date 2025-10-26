'use client';

import * as React from 'react';
import { motion, isMotionComponent, type HTMLMotionProps } from 'framer-motion';
import { cn } from '@/lib/utils';

type AnyProps = Record<string, unknown>;

type DOMMotionProps<T extends HTMLElement = HTMLElement> = Omit<
  HTMLMotionProps<keyof HTMLElementTagNameMap>,
  'ref'
> & { ref?: React.Ref<T> };

type WithAsChild<Base extends object> =
  | (Base & { asChild: true; children: React.ReactElement })
  | (Base & { asChild?: false | undefined });

type SlotProps<T extends HTMLElement = HTMLElement> = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  children?: any;
} & DOMMotionProps<T>;

// TODO: Implement ref merging if needed
// function mergeRefs<T>(
//   ...refs: (React.Ref<T> | undefined)[]
// ): React.RefCallback<T> {
//   return (node) => {
//     refs.forEach((ref) => {
//       if (!ref) return;
//       if (typeof ref === 'function') {
//         ref(node);
//       } else {
//         (ref as React.RefObject<T | null>).current = node;
//       }
//     });
//   };
// }

function mergeProps<T extends HTMLElement>(
  childProps: AnyProps,
  slotProps: DOMMotionProps<T>,
): AnyProps {
  const merged: AnyProps = { ...childProps, ...slotProps };

  if (childProps.className || slotProps.className) {
    merged.className = cn(
      childProps.className as string,
      slotProps.className as string,
    );
  }

  if (childProps.style || slotProps.style) {
    merged.style = {
      ...(childProps.style as React.CSSProperties),
      ...(slotProps.style as React.CSSProperties),
    };
  }

  return merged;
}

function Slot<T extends HTMLElement = HTMLElement>({
  children,
  ref,
  ...props
}: SlotProps<T>) {
  // Check if child is already a motion component
  const isAlreadyMotion =
    React.isValidElement(children) &&
    typeof children.type === 'object' &&
    children.type !== null &&
    isMotionComponent(children.type);

  if (!React.isValidElement(children)) return null;

  // Use motion directly for non-motion components, or pass through if already motion
  const Component = isAlreadyMotion ? children.type : motion.div;

  const { ref: _childRef, ...childProps } = children.props as AnyProps;
  const mergedProps = mergeProps(childProps, props);

  // If already a motion component, use it directly
  if (isAlreadyMotion) {
    return React.cloneElement(children, mergedProps);
  }

  // For non-motion components, wrap with motion
  return (
    <Component {...mergedProps} ref={ref}>
      {children}
    </Component>
  );
}

export {
  Slot,
  type SlotProps,
  type WithAsChild,
  type DOMMotionProps,
  type AnyProps,
  // mergeRefs, // TODO: Uncomment when implementing ref merging
};
