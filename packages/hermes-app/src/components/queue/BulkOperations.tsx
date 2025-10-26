import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Trash2, X, CheckSquare, Square, RefreshCw } from 'lucide-react'
import { useConfirmation } from '@/hooks/useConfirmation'
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog'

interface BulkOperationItem {
  id: string
  title: string
  filePath?: string
  status: string
}

interface BulkOperationsProps {
  selectedCount: number
  totalCount: number
  selectedItems: BulkOperationItem[]
  onSelectAll: () => void
  onDeselectAll: () => void
  onBulkDelete: () => void
  onBulkCancel: () => void
  isProcessing: boolean
}

export function BulkOperations({
  selectedCount,
  totalCount,
  selectedItems,
  onSelectAll,
  onDeselectAll,
  onBulkDelete,
  onBulkCancel,
  isProcessing,
}: BulkOperationsProps) {
  const { isOpen, title, description, confirmText, cancelText, variant, showConfirmation, hideConfirmation, confirm } = useConfirmation()

  const handleBulkDelete = () => {
    showConfirmation({
      title: 'Delete Multiple Files',
      description: `Are you sure you want to delete ${selectedCount} selected ${selectedCount === 1 ? 'file' : 'files'}? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      variant: 'destructive',
      onConfirm: onBulkDelete,
    })
  }

  const handleBulkCancel = () => {
    showConfirmation({
      title: 'Cancel Multiple Downloads',
      description: `Are you sure you want to cancel ${selectedCount} selected downloads?`,
      confirmText: 'Cancel Downloads',
      cancelText: 'Keep Downloads',
      variant: 'destructive',
      onConfirm: onBulkCancel,
    })
  }

  if (selectedCount === 0) {
    return null
  }

  const hasCancellableItems = selectedItems.some(item =>
    item.status === 'queued' || item.status === 'downloading' || item.status === 'processing'
  )

  return (
    <>
      <Card className="border-primary/50 bg-primary/5">
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <CheckSquare className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {selectedCount} of {totalCount} selected
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={selectedCount === totalCount ? onDeselectAll : onSelectAll}
                  disabled={isProcessing}
                >
                  {selectedCount === totalCount ? (
                    <>
                      <Square className="h-4 w-4 mr-1" />
                      Deselect All
                    </>
                  ) : (
                    <>
                      <CheckSquare className="h-4 w-4 mr-1" />
                      Select All
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {hasCancellableItems && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleBulkCancel}
                  disabled={isProcessing}
                  className="text-orange-600 hover:text-orange-700"
                >
                  <X className="h-4 w-4 mr-1" />
                  Cancel ({selectedCount})
                </Button>
              )}

              <Button
                variant="outline"
                size="sm"
                onClick={handleBulkDelete}
                disabled={isProcessing}
                className="text-destructive hover:text-destructive"
              >
                {isProcessing ? (
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4 mr-1" />
                )}
                Delete ({selectedCount})
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <ConfirmationDialog
        isOpen={isOpen}
        onClose={hideConfirmation}
        onConfirm={confirm}
        title={title || 'Are you sure?'}
        description={description || 'This action cannot be undone.'}
        confirmText={confirmText || 'Confirm'}
        cancelText={cancelText || 'Cancel'}
        variant={variant || 'default'}
      />
    </>
  )
}
