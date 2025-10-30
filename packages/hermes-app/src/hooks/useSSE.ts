import { useEffect, useState, useRef, useCallback } from 'react';

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

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        setIsReconnecting(false);
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);
        onOpen?.();
      };

      eventSource.onerror = () => {
        setIsConnected(false);

        // EventSource immediately closes on HTTP errors (403, 401, etc.)
        // Check readyState after a brief delay to detect permanent failures
        const checkForAuthError = () => {
          if (eventSource.readyState === EventSource.CLOSED) {
            // Connection closed immediately = likely auth error (403/401)
            // Don't retry auth failures
            console.error('SSE connection closed immediately - likely auth failure, not retrying');
            shouldReconnectRef.current = false;
            const err = new Error('SSE authentication failed');
            setError(err);
            onError?.(err);
            onClose?.();
            return true;
          }
          return false;
        };

        // Check immediately for CLOSED state
        if (checkForAuthError()) {
          return;
        }

        // If not immediately closed, it's a network error - can retry
        const err = new Error('SSE connection error');
        setError(err);
        onError?.(err);

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
            connectRef.current?.();
          }, delay);
        } else {
          onClose?.();
        }
      };

      // Listen for specified events
      if (events.length > 0) {
        events.forEach((eventType) => {
          eventSource.addEventListener(eventType, (event: MessageEvent) => {
            // Skip empty messages (heartbeats/keepalives)
            if (!event.data || event.data.trim() === '') {
              return;
            }

            try {
              const parsedData = JSON.parse(event.data);
              setData(parsedData);
            } catch (e) {
              // Only log parse errors for non-empty data
              if (event.data.trim() !== '') {
                console.error('Failed to parse SSE data:', e, 'Data:', event.data);
              }
            }
          });
        });
      } else {
        // Listen for all messages
        eventSource.onmessage = (event: MessageEvent) => {
          // Skip empty messages (heartbeats/keepalives)
          if (!event.data || event.data.trim() === '') {
            return;
          }

          try {
            const parsedData = JSON.parse(event.data);
            setData(parsedData);
          } catch (e) {
            // Only log parse errors for non-empty data
            if (event.data.trim() !== '') {
              console.error('Failed to parse SSE data:', e, 'Data:', event.data);
            }
          }
        };
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to create SSE connection');
      setError(error);
      onError?.(error);
    }
  }, [url, reconnect, maxReconnectAttempts, reconnectDelay, maxReconnectDelay, events, onOpen, onClose, onError]);

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
