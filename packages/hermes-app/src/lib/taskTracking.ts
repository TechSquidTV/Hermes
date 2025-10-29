// Event-based task tracking with cross-tab synchronization

import { debug } from '@/lib/debug'

const TASK_TRACKING_KEY = 'hermes_tracked_tasks' // Use localStorage
const TASK_EVENT_KEY = 'hermes_task_event' // For cross-tab events

export interface TaskEvent {
  taskId: string
  action: 'added' | 'removed' | 'cleared'
  timestamp: number
}

class TaskTracker {
  private listeners: Set<(taskIds: string[]) => void> = new Set()
  private storageListenerAttached = false

  constructor() {
    // Listen for storage events from other tabs
    if (typeof window !== 'undefined') {
      this.attachStorageListener()
    }
  }

  private attachStorageListener() {
    if (this.storageListenerAttached) return

    window.addEventListener('storage', (e) => {
      // Only listen to our specific keys
      if (e.key === TASK_TRACKING_KEY && e.newValue !== e.oldValue) {
        const taskIds = this.getTasks()
        this.notifyListeners(taskIds)
      }

      // Handle task events from other tabs
      if (e.key === TASK_EVENT_KEY && e.newValue) {
        try {
          const event: TaskEvent = JSON.parse(e.newValue)
          // Dispatch custom event for this tab
          window.dispatchEvent(new CustomEvent('taskEvent', { detail: event }))
        } catch (error) {
          debug.taskTracking('Failed to parse task event:', error)
        }
      }
    })

    this.storageListenerAttached = true
  }

  addTask(taskId: string) {
    const current = this.getTasks()
    if (current.includes(taskId)) {
      return // Already tracked
    }

    const updated = [...current, taskId]
    localStorage.setItem(TASK_TRACKING_KEY, JSON.stringify(updated))

    // Emit event for cross-tab sync
    const event: TaskEvent = {
      taskId,
      action: 'added',
      timestamp: Date.now()
    }
    localStorage.setItem(TASK_EVENT_KEY, JSON.stringify(event))

    // Notify listeners in this tab
    this.notifyListeners(updated)

    // Dispatch custom event for this tab
    window.dispatchEvent(new CustomEvent('taskAdded', { detail: event }))
  }

  removeTask(taskId: string) {
    const current = this.getTasks()
    const updated = current.filter(id => id !== taskId)

    if (updated.length === current.length) {
      return // Task wasn't in the list
    }

    localStorage.setItem(TASK_TRACKING_KEY, JSON.stringify(updated))

    // Emit event for cross-tab sync
    const event: TaskEvent = {
      taskId,
      action: 'removed',
      timestamp: Date.now()
    }
    localStorage.setItem(TASK_EVENT_KEY, JSON.stringify(event))

    this.notifyListeners(updated)
    window.dispatchEvent(new CustomEvent('taskRemoved', { detail: event }))
  }

  getTasks(): string[] {
    try {
      const stored = localStorage.getItem(TASK_TRACKING_KEY)
      return stored ? JSON.parse(stored) : []
    } catch (error) {
      debug.taskTracking('Failed to get tasks:', error)
      return []
    }
  }

  clearTasks() {
    localStorage.removeItem(TASK_TRACKING_KEY)

    const event: TaskEvent = {
      taskId: '',
      action: 'cleared',
      timestamp: Date.now()
    }
    localStorage.setItem(TASK_EVENT_KEY, JSON.stringify(event))

    this.notifyListeners([])
  }

  subscribe(listener: (taskIds: string[]) => void) {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private notifyListeners(taskIds: string[]) {
    this.listeners.forEach(listener => {
      try {
        listener(taskIds)
      } catch (error) {
        debug.taskTracking('Listener error:', error)
      }
    })
  }
}

export const taskTracker = new TaskTracker()
