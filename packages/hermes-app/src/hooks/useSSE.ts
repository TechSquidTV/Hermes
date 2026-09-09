import { useEffect, useState, useRef, useCallback, useMemo } from 'react';

// Stable default to prevent unnecessary re-renders
const DEFAULT_EVENTS: string[] = [];

export interface SSEOptions {
  /**
   * Enable automatic reconnection on disconnect
   */
  reconnect?: boolean;

  /**
   * Maximum number of reconnection attempts (0 = infinite)
   */
  maxReconnectAttempts?: number;

  /**
   * Initial reconnection delay in milliseconds
   */
  reconnectDelay?: number;

  /**
   * Maximum reconnection delay in milliseconds
   */
  maxReconnectDelay?: number;

  /**
   * Event types to listen for
   */
  events?: string[];

  /**
   * Callback when connection opens
   */
  onOpen?: () => void;

  /**
   * Callback when connection closes
   */
  onClose?: () => void;

  /**
   * Callback when error occurs
   */
  onError?: (error: Error) => void;
}

export interface SSEState<T = unknown> {
  /**
   * Latest received data
   */
  data: T | null;

  /**
   * Connection status
   */
  isConnected: boolean;

  /**
   * Error state
   */
  error: Error | null;

  /**
   * Is currently attempting to reconnect
   */
  isReconnecting: boolean;

  /**
   * Number of reconnection attempts
   */
  reconnectAttempts: number;

  /**
   * Manually close the connection
   */
  close: () => void;

  /**
   * Manually reconnect
   */
  reconnect: () => void;
}

/**
 * Hook for Server-Sent Events (SSE) with automatic reconnection
 *
 * @param url - SSE endpoint URL
 * @param options - Configuration options
 * @returns SSE state and controls
 *
 * @example
 * ```tsx
 * const { data, isConnected, error } = useSSE(
 *   '/api/v1/events/stream?channels=download:updates',
 *   {
 *     reconnect: true,
 *     maxReconnectAttempts: 5,
 *     events: ['download_progress', 'queue_update'],
 *     onOpen: () => console.log('Connected'),
 *     onError: (err) => console.error('SSE error:', err)
 *   }
 * );
 * ```
 */
export function useSSE<T = unknown>(
  url: string | null,
  options: SSEOptions = {}
): SSEState<T> {
  const {
    reconnect = true,
    maxReconnectAttempts = 5,
    reconnectDelay = 1000,
    maxReconnectDelay = 30000,
    events = DEFAULT_EVENTS,
    onOpen,
    onClose,
    onError,
  } = options;

  const eventTypesKey = JSON.stringify(events);
  const eventTypes = useMemo<string[]>(() => JSON.parse(eventTypesKey), [eventTypesKey]);
  const callbacksRef = useRef({ onOpen, onClose, onError });
  useEffect(() => {
    callbacksRef.current = { onOpen, onClose, onError };
  }, [onOpen, onClose, onError]);

  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);
  const reconnectAttemptsRef = useRef(0);
  const connectRef = useRef<(() => void) | null>(null);

  const close = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setIsReconnecting(false);
  }, []);

  const connect = useCallback(() => {
    if (!url) return;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        if (eventSourceRef.current !== eventSource) return;
        setIsConnected(true);
        setError(null);
        setIsReconnecting(false);
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);
        callbacksRef.current.onOpen?.();
      };

      eventSource.onerror = () => {
        if (eventSourceRef.current !== eventSource) return;
        setIsConnected(false);
        const permanentlyClosed = eventSource.readyState === EventSource.CLOSED;
        // Own reconnection here, so the browser cannot retry alongside our timer.
        eventSource.close();
        eventSourceRef.current = null;
        setIsReconnecting(false);

        // A CLOSED source is terminal; EventSource does not expose its HTTP status.
        if (permanentlyClosed) {
          shouldReconnectRef.current = false;
          const err = new Error('SSE connection closed');
          setError(err);
          callbacksRef.current.onError?.(err);
          callbacksRef.current.onClose?.();
          return;
        }

        // If not immediately closed, it's a network error - can retry
        const err = new Error('SSE connection error');
        setError(err);
        callbacksRef.current.onError?.(err);

        // Attempt reconnection for network errors
        if (
          shouldReconnectRef.current &&
          reconnect &&
          (maxReconnectAttempts === 0 || reconnectAttemptsRef.current < maxReconnectAttempts)
        ) {
          setIsReconnecting(true);
          reconnectAttemptsRef.current += 1;
          setReconnectAttempts(reconnectAttemptsRef.current);

          // Exponential backoff with max delay
          const delay = Math.min(
            reconnectDelay * Math.pow(2, reconnectAttemptsRef.current - 1),
            maxReconnectDelay
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            if (shouldReconnectRef.current) connectRef.current?.();
          }, delay);
        } else {
          callbacksRef.current.onClose?.();
        }
      };

      const handleMessage = (event: MessageEvent<string>) => {
        if (eventSourceRef.current !== eventSource || !event.data.trim()) return;
        try {
          const parsedData: T = JSON.parse(event.data);
          setData(parsedData);
        } catch (error) {
          console.error('Failed to parse SSE data:', error, 'Data:', event.data);
        }
      };

      if (eventTypes.length > 0) {
        eventTypes.forEach((eventType) => {
          eventSource.addEventListener(eventType, handleMessage);
        });
      } else {
        eventSource.onmessage = handleMessage;
      }

    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create SSE connection');
      setError(error);
      callbacksRef.current.onError?.(error);
    }
  }, [url, reconnect, maxReconnectAttempts, reconnectDelay, maxReconnectDelay, eventTypes]);

  // Store connect in ref to avoid closure issues
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    if (url) {
      shouldReconnectRef.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect
      connect();
    }

    return () => {
      close();
    };
  }, [url, connect, close]);

  const manualReconnect = useCallback(() => {
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    setReconnectAttempts(0);
    connect();
  }, [connect]);

  return {
    data,
    isConnected,
    error,
    isReconnecting,
    reconnectAttempts,
    close,
    reconnect: manualReconnect,
  };
}
