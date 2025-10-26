/* eslint-disable react-hooks/preserve-manual-memoization */
'use client';

import * as React from 'react';
import { AnimatePresence, motion, type Transition } from 'framer-motion';

import { cn } from '@/lib/utils';

type HighlightMode = 'children' | 'parent';

type Bounds = {
  top: number;
  left: number;
  width: number;
  height: number;
};

type HighlightContextType<T extends string> = {
  as?: keyof HTMLElementTagNameMap;
  mode: HighlightMode;
  activeValue: T | null;
  setActiveValue: (value: T | null) => void;
  setBounds: (bounds: DOMRect) => void;
  clearBounds: () => void;
  id: string;
  hover: boolean;
  click: boolean;
  className?: string;
  style?: React.CSSProperties;
  activeClassName?: string;
  setActiveClassName: (className: string) => void;
  transition?: Transition;
  disabled?: boolean;
  enabled?: boolean;
  exitDelay?: number;
  forceUpdateBounds?: boolean;
};

const HighlightContext = React.createContext<
  HighlightContextType<string> | undefined
>(undefined);

function useHighlight<T extends string = string>(): HighlightContextType<T> {
  const context = React.useContext(HighlightContext);
  if (!context) {
    throw new Error('useHighlight must be used within a HighlightProvider');
  }
  return context as unknown as HighlightContextType<T>;
}

type BaseHighlightProps<T extends React.ElementType = 'div'> = {
  as?: T;
  ref?: React.Ref<HTMLDivElement>;
  mode?: HighlightMode;
  value?: string | null;
  defaultValue?: string | null;
  onValueChange?: (value: string | null) => void;
  className?: string;
  style?: React.CSSProperties;
  transition?: Transition;
  hover?: boolean;
  click?: boolean;
  disabled?: boolean;
  enabled?: boolean;
  exitDelay?: number;
};

type ParentModeHighlightProps = {
  boundsOffset?: Partial<Bounds>;
  containerClassName?: string;
  forceUpdateBounds?: boolean;
};

type ControlledParentModeHighlightProps<T extends React.ElementType = 'div'> =
  BaseHighlightProps<T> &
    ParentModeHighlightProps & {
      mode: 'parent';
      controlledItems: true;
      children: React.ReactNode;
    };

type ControlledChildrenModeHighlightProps<T extends React.ElementType = 'div'> =
  BaseHighlightProps<T> & {
    mode?: 'children' | undefined;
    controlledItems: true;
    children: React.ReactNode;
  };

type UncontrolledParentModeHighlightProps<T extends React.ElementType = 'div'> =
  BaseHighlightProps<T> &
    ParentModeHighlightProps & {
      mode: 'parent';
      controlledItems?: false;
      itemsClassName?: string;
      children: React.ReactElement | React.ReactElement[];
    };

type UncontrolledChildrenModeHighlightProps<
  T extends React.ElementType = 'div',
> = BaseHighlightProps<T> & {
  mode?: 'children';
  controlledItems?: false;
  itemsClassName?: string;
  children: React.ReactElement | React.ReactElement[];
};

type HighlightProps<T extends React.ElementType = 'div'> =
  | ControlledParentModeHighlightProps<T>
  | ControlledChildrenModeHighlightProps<T>
  | UncontrolledParentModeHighlightProps<T>
  | UncontrolledChildrenModeHighlightProps<T>;

function Highlight<T extends React.ElementType = 'div'>({
  ref,
  ...props
}: HighlightProps<T>) {
  const {
    as: Component = 'div',
    children,
    value,
    defaultValue,
    onValueChange,
    className,
    style,
    transition = { type: 'spring', stiffness: 350, damping: 35 },
    hover = false,
    click = true,
    enabled = true,
    controlledItems,
    disabled = false,
    exitDelay = 200,
    mode = 'children',
  } = props;

  // Extract parent mode specific props safely
  const parentProps = mode === 'parent' ? props as ParentModeHighlightProps : {};
  const boundsOffset = parentProps.boundsOffset;
  const containerClassName = parentProps.containerClassName;
  const forceUpdateBounds = parentProps.forceUpdateBounds;

  const localRef = React.useRef<HTMLDivElement>(null);
  React.useImperativeHandle(ref, () => localRef.current as HTMLDivElement);

  const [activeValue, setActiveValue] = React.useState<string | null>(
    value ?? defaultValue ?? null,
  );
  const [boundsState, setBoundsState] = React.useState<Bounds | null>(null);
  const [activeClassNameState, setActiveClassNameState] =
    React.useState<string>('');

  // Create a stable callback reference for onValueChange to avoid React Compiler issues
  const stableOnValueChange = React.useCallback(
    (value: string | null) => {
      onValueChange?.(value);
    },
    [onValueChange],
  );

  const safeSetActiveValue = React.useCallback(
    (id: string | null) => {
      setActiveValue((prev) => (prev === id ? prev : id));
      stableOnValueChange(id);
    },
    [stableOnValueChange],
  );

  const safeSetBounds = React.useCallback(
    (bounds: DOMRect) => {
      if (!localRef.current) return;

      const offset = boundsOffset ?? {
        top: 0,
        left: 0,
        width: 0,
        height: 0,
      };

      const containerRect = localRef.current.getBoundingClientRect();
      const newBounds: Bounds = {
        top: bounds.top - containerRect.top + (offset.top ?? 0),
        left: bounds.left - containerRect.left + (offset.left ?? 0),
        width: bounds.width + (offset.width ?? 0),
        height: bounds.height + (offset.height ?? 0),
      };

      setBoundsState((prev) => {
        if (
          prev &&
          prev.top === newBounds.top &&
          prev.left === newBounds.left &&
          prev.width === newBounds.width &&
          prev.height === newBounds.height
        ) {
          return prev;
        }
        return newBounds;
      });
    },
    [boundsOffset],
  );

  const clearBounds = React.useCallback(() => {
    setBoundsState((prev) => (prev === null ? prev : null));
  }, []);

  React.useEffect(() => {
    if (value !== undefined) setActiveValue(value);
    else if (defaultValue !== undefined) setActiveValue(defaultValue);
  }, [value, defaultValue]);

  const id = React.useId();

  React.useEffect(() => {
    if (mode !== 'parent') return;
    const container = localRef.current;
    if (!container) return;

    const onScroll = () => {
      if (!activeValue) return;
      const activeEl = container.querySelector<HTMLElement>(
        `[data-value="${activeValue}"][data-highlight="true"]`,
      );
      if (activeEl) safeSetBounds(activeEl.getBoundingClientRect());
    };

    container.addEventListener('scroll', onScroll, { passive: true });
    return () => container.removeEventListener('scroll', onScroll);
  }, [mode, activeValue, safeSetBounds]);

  // containerClassName is already destructured above

  // Create stable references for values that React Compiler suspects might be mutated
  const stableTransition = React.useMemo(() => transition,
    [transition]);
  const stableStyle = React.useMemo(() => style,
    [style]);
  const stableClassName = React.useMemo(() => className,
    [className]);
  const stableContainerClassName = React.useMemo(() => containerClassName,
    [containerClassName]);

  const render = React.useCallback(
    (children: React.ReactNode) => {
      if (mode === 'parent') {
        return (
          <Component
            ref={localRef}
            data-slot="motion-highlight-container"
            style={{ position: 'relative', zIndex: 1 }}
            className={stableContainerClassName}
          >
            <AnimatePresence initial={false} mode="wait">
              {boundsState && (
                <motion.div
                  data-slot="motion-highlight"
                  animate={{
                    top: boundsState.top,
                    left: boundsState.left,
                    width: boundsState.width,
                    height: boundsState.height,
                    opacity: 1,
                  }}
                  initial={{
                    top: boundsState.top,
                    left: boundsState.left,
                    width: boundsState.width,
                    height: boundsState.height,
                    opacity: 0,
                  }}
                  exit={{
                    opacity: 0,
                    transition: {
                      ...stableTransition,
                      delay: (stableTransition?.delay ?? 0) + (exitDelay ?? 0) / 1000,
                    },
                  }}
                  transition={stableTransition}
                  style={{ position: 'absolute', zIndex: 0, ...stableStyle }}
                  className={cn(stableClassName, activeClassNameState)}
                />
              )}
            </AnimatePresence>
            {children}
          </Component>
        );
      }

      return children;
    },
    [
      mode,
      Component,
      stableContainerClassName,
      boundsState,
      stableTransition,
      exitDelay,
      stableStyle,
      stableClassName,
      activeClassNameState,
    ],
  );

  return (
    <HighlightContext.Provider
      value={{
        mode,
        activeValue,
        setActiveValue: safeSetActiveValue,
        id,
        hover,
        click,
        className,
        style,
        transition,
        disabled,
        enabled,
        exitDelay,
        setBounds: safeSetBounds,
        clearBounds,
        activeClassName: activeClassNameState,
        setActiveClassName: setActiveClassNameState,
        forceUpdateBounds,
      }}
    >
      {enabled
        ? controlledItems
          ? render(children)
          : render(
              React.Children.map(children, (child, index) => (
                <HighlightItem key={index} className={props?.itemsClassName}>
                  {child}
                </HighlightItem>
              )),
            )
        : children}
    </HighlightContext.Provider>
  );
}

function getNonOverridingDataAttributes(
  element: React.ReactElement,
  dataAttributes: Record<string, unknown>,
): Record<string, unknown> {
  return Object.keys(dataAttributes).reduce<Record<string, unknown>>(
    (acc, key) => {
      if ((element.props as Record<string, unknown>)[key] === undefined) {
        acc[key] = dataAttributes[key];
      }
      return acc;
    },
    {},
  );
}

type ExtendedChildProps = React.ComponentProps<'div'> & {
  id?: string;
  ref?: React.Ref<HTMLElement>;
  'data-active'?: string;
  'data-value'?: string;
  'data-disabled'?: boolean;
  'data-highlight'?: boolean;
  'data-slot'?: string;
};

type HighlightItemProps<T extends React.ElementType = 'div'> =
  React.ComponentProps<T> & {
    as?: T;
    children: React.ReactElement;
    id?: string;
    value?: string;
    className?: string;
    style?: React.CSSProperties;
    transition?: Transition;
    activeClassName?: string;
    disabled?: boolean;
    exitDelay?: number;
    asChild?: boolean;
    forceUpdateBounds?: boolean;
  };

function HighlightItem<T extends React.ElementType>({
  ref,
  as,
  children,
  id,
  value,
  className,
  style,
  transition,
  disabled = false,
  activeClassName,
  exitDelay,
  asChild = false,
  forceUpdateBounds,
  ...props
}: HighlightItemProps<T>) {
  const itemId = React.useId();
  const {
    activeValue,
    setActiveValue,
    mode,
    setBounds,
    clearBounds,
    hover,
    click,
    enabled,
    className: contextClassName,
    style: contextStyle,
    transition: contextTransition,
    id: contextId,
    disabled: contextDisabled,
    exitDelay: contextExitDelay,
    forceUpdateBounds: contextForceUpdateBounds,
    setActiveClassName,
  } = useHighlight();

  const Component = as ?? 'div';
  const element = children as React.ReactElement<ExtendedChildProps>;
  const childValue =
    id ?? value ?? element.props?.['data-value'] ?? element.props?.id ?? itemId;
  const isActive = activeValue === childValue;
  const isDisabled = disabled === undefined ? contextDisabled : disabled;
  // Create stable transition reference
  const stableItemTransition = React.useMemo(
    () => transition ?? contextTransition,
    [transition, contextTransition]
  );

  const localRef = React.useRef<HTMLDivElement>(null);
  React.useImperativeHandle(ref, () => localRef.current as HTMLDivElement);

  // Create stable references for values that might be mutated
  const stableActiveClassName = React.useMemo(() => activeClassName,
    [activeClassName]);

  React.useEffect(() => {
    if (mode !== 'parent') return;
    let rafId: number;
    let previousBounds: Bounds | null = null;
    const shouldUpdateBounds =
      forceUpdateBounds === true ||
      (contextForceUpdateBounds && forceUpdateBounds !== false);

    const updateBounds = () => {
      if (!localRef.current) return;

      const bounds = localRef.current.getBoundingClientRect();

      if (shouldUpdateBounds) {
        if (
          previousBounds &&
          previousBounds.top === bounds.top &&
          previousBounds.left === bounds.left &&
          previousBounds.width === bounds.width &&
          previousBounds.height === bounds.height
        ) {
          rafId = requestAnimationFrame(updateBounds);
          return;
        }
        previousBounds = bounds;
        rafId = requestAnimationFrame(updateBounds);
      }

      setBounds(bounds);
    };

    if (isActive) {
      updateBounds();
      setActiveClassName(stableActiveClassName ?? '');
    } else if (!activeValue) clearBounds();

    if (shouldUpdateBounds) return () => cancelAnimationFrame(rafId);
  },
  [
    mode,
    isActive,
    activeValue,
    setBounds,
    clearBounds,
    stableActiveClassName,
    setActiveClassName,
    forceUpdateBounds,
    contextForceUpdateBounds,
  ]);

  if (!React.isValidElement(children)) return children;

  const dataAttributes = {
    'data-active': isActive ? 'true' : 'false',
    'aria-selected': isActive,
    'data-disabled': isDisabled,
    'data-value': childValue,
    'data-highlight': true,
  };

  const commonHandlers = hover
    ? {
        onMouseEnter: (e: React.MouseEvent<HTMLDivElement>) => {
          setActiveValue(childValue);
          element.props.onMouseEnter?.(e);
        },
        onMouseLeave: (e: React.MouseEvent<HTMLDivElement>) => {
          setActiveValue(null);
          element.props.onMouseLeave?.(e);
        },
      }
    : click
      ? {
          onClick: (e: React.MouseEvent<HTMLDivElement>) => {
            setActiveValue(childValue);
            element.props.onClick?.(e);
          },
        }
      : {};

  if (asChild) {
    if (mode === 'children') {
      return (
        <div
          key={childValue}
          ref={localRef}
          className={cn('relative', element.props.className)}
          {...getNonOverridingDataAttributes(element, {
            ...dataAttributes,
            'data-slot': 'motion-highlight-item-container',
          })}
          {...commonHandlers}
          {...props}
        >
          <AnimatePresence initial={false} mode="wait">
            {isActive && !isDisabled && (
              <motion.div
                layoutId={`transition-background-${contextId}`}
                data-slot="motion-highlight"
                style={{
                  position: 'absolute',
                  zIndex: 0,
                  ...contextStyle,
                  ...style,
                }}
                className={cn(contextClassName, activeClassName)}
                transition={stableItemTransition}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{
                  opacity: 0,
                  transition: {
                    ...stableItemTransition,
                    delay:
                      (stableItemTransition?.delay ?? 0) +
                      (exitDelay ?? contextExitDelay ?? 0) / 1000,
                  },
                }}
                {...dataAttributes}
              />
            )}
          </AnimatePresence>
          {React.cloneElement(element, {
            ...element.props,
            ...commonHandlers,
            ...getNonOverridingDataAttributes(element, dataAttributes),
          })}
        </div>
      );
    }

    // For non-children mode, create a simple wrapper
    return (
      <div
        ref={localRef}
        {...getNonOverridingDataAttributes(element, {
          ...dataAttributes,
          'data-slot': 'motion-highlight-item',
        })}
        {...commonHandlers}
      >
        {React.cloneElement(element, element.props)}
      </div>
    );
  }

  return enabled ? (
    <Component
      key={childValue}
      ref={localRef}
      data-slot="motion-highlight-item-container"
      className={cn(mode === 'children' && 'relative', className)}
      {...dataAttributes}
      {...props}
      {...commonHandlers}
    >
      {mode === 'children' && (
        <AnimatePresence initial={false} mode="wait">
          {isActive && !isDisabled && (
            <motion.div
              layoutId={`transition-background-${contextId}`}
              data-slot="motion-highlight"
              style={{
                position: 'absolute',
                zIndex: 0,
                ...contextStyle,
                ...style,
              }}
              className={cn(contextClassName, activeClassName)}
              transition={stableItemTransition}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{
                opacity: 0,
                  transition: {
                    ...stableItemTransition,
                    delay:
                      (stableItemTransition?.delay ?? 0) +
                      (exitDelay ?? contextExitDelay ?? 0) / 1000,
                  },
              }}
              {...dataAttributes}
            />
          )}
        </AnimatePresence>
      )}

      {React.cloneElement(element, {
        style: { position: 'relative', zIndex: 1 },
        className: element.props.className,
        ...getNonOverridingDataAttributes(element, {
          ...dataAttributes,
          'data-slot': 'motion-highlight-item',
        }),
      })}
    </Component>
  ) : (
    children
  );
}

export {
  Highlight,
  HighlightItem,
  useHighlight,
  type HighlightProps,
  type HighlightItemProps,
};
