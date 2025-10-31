/**
 * Tests for ConnectionStatus component
 *
 * This component displays SSE connection status to users,
 * showing whether they're connected, reconnecting, or disconnected.
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConnectionStatus } from './ConnectionStatus'

describe('ConnectionStatus', () => {
  describe('Connected State', () => {
    it('shows connected indicator when isConnected is true', () => {
      render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.getByText(/connected/i)).toBeInTheDocument()
    })

    it('applies success styling when connected', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      // Look for green/success color classes
      const statusElement = container.querySelector('[class*="green"]')
      expect(statusElement).toBeInTheDocument()
    })
  })

  describe('Reconnecting State', () => {
    it('shows reconnecting indicator when isReconnecting is true', () => {
      render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={2}
        />
      )

      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()
    })

    it('displays reconnect attempt count', () => {
      render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={3}
        />
      )

      // Should show attempt number
      expect(screen.getByText(/3/)).toBeInTheDocument()
    })

    it('applies warning styling when reconnecting', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={2}
        />
      )

      // Look for yellow/warning color classes
      const statusElement = container.querySelector('[class*="yellow"], [class*="amber"]')
      expect(statusElement).toBeInTheDocument()
    })
  })

  describe('Disconnected State', () => {
    it('shows disconnected indicator when not connected and not reconnecting', () => {
      render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.getByText(/disconnected/i)).toBeInTheDocument()
    })

    it('applies error styling when disconnected', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      // Look for red/error color classes
      const statusElement = container.querySelector('[class*="red"]')
      expect(statusElement).toBeInTheDocument()
    })
  })

  describe('State Transitions', () => {
    it('updates from connected to reconnecting', () => {
      const { rerender } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.getByText(/connected/i)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={1}
        />
      )

      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()
    })

    it('updates from reconnecting to connected', () => {
      const { rerender } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={2}
        />
      )

      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.getByText(/connected/i)).toBeInTheDocument()
    })

    it('updates from reconnecting to disconnected', () => {
      const { rerender } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={5}
        />
      )

      expect(screen.getByText(/reconnecting/i)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={false}
          reconnectAttempts={10}
        />
      )

      expect(screen.getByText(/disconnected/i)).toBeInTheDocument()
    })
  })

  describe('Reconnect Attempts', () => {
    it('shows incrementing reconnect attempts', () => {
      const { rerender } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={1}
        />
      )

      expect(screen.getByText(/1/)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={2}
        />
      )

      expect(screen.getByText(/2/)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={3}
        />
      )

      expect(screen.getByText(/3/)).toBeInTheDocument()
    })

    it('resets reconnect attempts when reconnected', () => {
      const { rerender } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={5}
        />
      )

      expect(screen.getByText(/5/)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.queryByText(/5/)).not.toBeInTheDocument()
    })
  })

  describe('Custom Styling', () => {
    it('accepts custom className', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
          className="custom-class"
        />
      )

      expect(container.querySelector('.custom-class')).toBeInTheDocument()
    })

    it('merges custom className with default classes', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
          className="my-custom-style"
        />
      )

      const element = container.firstChild
      expect(element).toHaveClass('my-custom-style')
    })
  })

  describe('Visual Indicators', () => {
    it('renders indicator icon when connected', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      // Look for the Wifi icon (from lucide-react)
      const icon = container.querySelector('svg')
      expect(icon).toBeInTheDocument()
      expect(icon).toHaveClass('lucide-wifi')
    })

    it('renders animated indicator when reconnecting', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={true}
          reconnectAttempts={1}
        />
      )

      // Should have animation classes when reconnecting
      const animatedElement = container.querySelector('[class*="animate"]')
      expect(animatedElement).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('provides accessible status text', () => {
      render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      // Screen readers should be able to read the connection status
      expect(screen.getByText(/connected/i)).toBeInTheDocument()
    })

    it('updates accessible status when state changes', () => {
      const { rerender } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.getByText(/connected/i)).toBeInTheDocument()

      rerender(
        <ConnectionStatus
          isConnected={false}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      expect(screen.getByText(/disconnected/i)).toBeInTheDocument()
    })
  })

  describe('Compact Display', () => {
    it('renders in compact mode', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      // Component should be relatively small/compact
      expect(container.firstChild).toBeInTheDocument()
    })

    it('displays minimal information when connected', () => {
      const { container } = render(
        <ConnectionStatus
          isConnected={true}
          isReconnecting={false}
          reconnectAttempts={0}
        />
      )

      // Should be concise - just a status indicator
      const text = container.textContent
      expect(text).toBeTruthy()
      expect(text!.length).toBeLessThan(50) // Should be short
    })
  })
})
