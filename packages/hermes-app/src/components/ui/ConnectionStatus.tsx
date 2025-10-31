import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

export interface ConnectionStatusProps {
  isConnected: boolean;
  isReconnecting?: boolean;
  reconnectAttempts?: number;
  className?: string;
}

/**
 * Visual indicator for SSE connection status
 */
export function ConnectionStatus({
  isConnected,
  isReconnecting = false,
  reconnectAttempts = 0,
  className = '',
}: ConnectionStatusProps) {
  if (isConnected) {
    return (
      <div className={`flex items-center gap-2 text-green-600 ${className}`}>
        <Wifi className="h-4 w-4" />
        <span className="text-sm">Connected</span>
      </div>
    );
  }

  if (isReconnecting) {
    return (
      <div className={`flex items-center gap-2 text-yellow-600 ${className}`}>
        <RefreshCw className="h-4 w-4 animate-spin" />
        <span className="text-sm">
          Reconnecting... (Attempt {reconnectAttempts})
        </span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 text-red-600 ${className}`}>
      <WifiOff className="h-4 w-4" />
      <span className="text-sm">Disconnected</span>
    </div>
  );
}
