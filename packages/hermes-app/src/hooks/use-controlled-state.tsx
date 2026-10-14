import * as React from 'react';

interface CommonControlledStateProps<T> {
  value?: T;
  defaultValue?: T;
}

export function useControlledState<T, Rest extends unknown[] = []>(
  props: CommonControlledStateProps<T> & {
    onChange?: (value: T, ...args: Rest) => void;
  },
): readonly [T, (next: T, ...args: Rest) => void] {
  const { value, defaultValue, onChange } = props;

  const [internalState, setInternalState] = React.useState<T>(
    value !== undefined ? value : (defaultValue as T),
  );
  const state = value !== undefined ? value : internalState;

  const setState = React.useCallback(
    (next: T, ...args: Rest) => {
      if (value === undefined) {
        setInternalState(next);
      }
      onChange?.(next, ...args);
    },
    [onChange, value],
  );

  return [state, setState] as const;
}
