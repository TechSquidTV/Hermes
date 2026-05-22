import { useState, useCallback } from 'react'
import { useDeleteFiles } from './useDownloadActions'
import { apiClient } from '@/services/api/client'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

interface BulkOperationItem {
  id: string
  title: string
  filePath?: string
  status: string
}

interface UseBulkOperationsOptions {
  onSuccess?: () => void
  onError?: (error: Error) => void
}

export function useBulkOperations(options: UseBulkOperationsOptions = {}) {
  const { onSuccess, onError } = options
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const [isProcessing, setIsProcessing] = useState(false)
  const queryClient = useQueryClient()

  const deleteMutation = useDeleteFiles()

  const selectItem = useCallback((id: string) => {
    setSelectedItems(prev => new Set(prev).add(id))
  }, [])

  const deselectItem = useCallback((id: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev)
      newSet.delete(id)
      return newSet
    })
  }, [])

  const selectAll = useCallback((items: BulkOperationItem[]) => {
    setSelectedItems(new Set(items.map(item => item.id)))
  }, [])

  const deselectAll = useCallback(() => {
    setSelectedItems(new Set())
  }, [])

  const toggleItem = useCallback((id: string) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }, [])

  const bulkDelete = useCallback(async (items: BulkOperationItem[]) => {
    const selectedItemIds = Array.from(selectedItems)
    if (selectedItemIds.length === 0) {
      toast.error('No items selected')
      return
    }

    const selectedItemsData = items.filter(item => selectedItemIds.includes(item.id))
    const filePaths = selectedItemsData
      .map(item => item.filePath)
      .filter((path): path is string => !!path)

    if (filePaths.length === 0) {
      toast.error('No downloadable files found in selection')
      return
    }

    // Note: UI confirmation should be handled in the component using this hook
    // The component should call showConfirmation() before calling bulkDelete
    // This allows for proper UI confirmation dialogs instead of browser confirm

    setIsProcessing(true)

    try {
      await deleteMutation.mutateAsync(filePaths)
      deselectAll()
      onSuccess?.()
    } catch (error) {
      onError?.(error as Error)
    } finally {
      setIsProcessing(false)
    }
  }, [selectedItems, deleteMutation, deselectAll, onSuccess, onError])

  const bulkRetry = useCallback(async () => {
    const selectedItemIds = Array.from(selectedItems)
    if (selectedItemIds.length === 0) {
      toast.error('No items selected')
      return
    }

    // TODO: Implement bulk retry functionality
    toast.info('Bulk retry coming soon!')
  }, [selectedItems])

  const bulkCancel = useCallback(async (items: BulkOperationItem[]) => {
    const selectedItemIds = Array.from(selectedItems)
    if (selectedItemIds.length === 0) {
      toast.error('No items selected')
      return
    }

    const cancellableItems = items.filter(item =>
      selectedItemIds.includes(item.id) &&
      (item.status === 'queued' || item.status === 'downloading' || item.status === 'processing')
    )

    if (cancellableItems.length === 0) {
      toast.error('No cancellable downloads found in selection')
      return
    }

    setIsProcessing(true)

    try {
      await Promise.all(cancellableItems.map(item => apiClient.cancelDownload(item.id)))
      toast.success(`Cancelled ${cancellableItems.length} download${cancellableItems.length !== 1 ? 's' : ''}`)
      deselectAll()
      queryClient.invalidateQueries({ queryKey: ['queue'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['queueStats'], exact: false })
      queryClient.invalidateQueries({ queryKey: ['recentDownloadsQueue'], exact: false })
      onSuccess?.()
    } catch (error) {
      toast.error(`Failed to cancel downloads: ${error instanceof Error ? error.message : 'Unknown error'}`)
      onError?.(error as Error)
    } finally {
      setIsProcessing(false)
    }
  }, [selectedItems, deselectAll, queryClient, onSuccess, onError])

  const getSelectedItems = useCallback((items: BulkOperationItem[]) => {
    const selectedIds = Array.from(selectedItems)
    return items.filter(item => selectedIds.includes(item.id))
  }, [selectedItems])

  return {
    selectedItems: selectedItems,
    selectedCount: selectedItems.size,
    isProcessing,

    // Selection methods
    selectItem,
    deselectItem,
    selectAll,
    deselectAll,
    toggleItem,

    // Bulk operations
    bulkDelete,
    bulkCancel,
    bulkRetry,

    // Utilities
    getSelectedItems,
    isAllSelected: (items: BulkOperationItem[]) => selectedItems.size === items.length,
    isNoneSelected: selectedItems.size === 0,
  }
}
