/**
 * Tests for taskTracker module
 *
 * Tests the task tracking functionality including the new
 * prepend behavior (newest tasks first)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { taskTracker } from '../taskTracking'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock window.dispatchEvent
const dispatchEventSpy = vi.spyOn(window, 'dispatchEvent')

describe('taskTracker', () => {
  beforeEach(() => {
    localStorageMock.clear()
    dispatchEventSpy.mockClear()
  })

  describe('addTask', () => {
    it('adds a new task to the beginning of the list (prepend)', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')

      const tasks = taskTracker.getTasks()

      // Newest task should be first
      expect(tasks[0]).toBe('task-3')
      expect(tasks[1]).toBe('task-2')
      expect(tasks[2]).toBe('task-1')
    })

    it('stores tasks in localStorage', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')

      const stored = JSON.parse(localStorageMock.getItem('hermes_tracked_tasks') || '[]')

      expect(stored).toEqual(['task-2', 'task-1'])
    })

    it('does not add duplicate tasks', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-1')

      const tasks = taskTracker.getTasks()

      expect(tasks.length).toBe(1)
      expect(tasks[0]).toBe('task-1')
    })

    it('dispatches custom event for this tab', () => {
      taskTracker.addTask('task-1')

      expect(dispatchEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'taskAdded',
          detail: expect.objectContaining({
            taskId: 'task-1',
            action: 'added',
          }),
        })
      )
    })

    it('handles empty task list correctly', () => {
      expect(taskTracker.getTasks()).toEqual([])

      taskTracker.addTask('first-task')

      expect(taskTracker.getTasks()).toEqual(['first-task'])
    })

    it('maintains order when adding multiple tasks', () => {
      const taskIds = ['task-1', 'task-2', 'task-3', 'task-4', 'task-5']

      taskIds.forEach(id => taskTracker.addTask(id))

      const tasks = taskTracker.getTasks()

      // Should be in reverse order (newest first)
      expect(tasks).toEqual(['task-5', 'task-4', 'task-3', 'task-2', 'task-1'])
    })
  })

  describe('removeTask', () => {
    it('removes a task from the list', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')

      taskTracker.removeTask('task-2')

      const tasks = taskTracker.getTasks()

      expect(tasks).toEqual(['task-3', 'task-1'])
      expect(tasks).not.toContain('task-2')
    })

    it('does nothing if task does not exist', () => {
      taskTracker.addTask('task-1')

      expect(() => taskTracker.removeTask('non-existent')).not.toThrow()

      const tasks = taskTracker.getTasks()
      expect(tasks).toEqual(['task-1'])
    })

    it('updates localStorage after removal', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')

      taskTracker.removeTask('task-1')

      const stored = JSON.parse(localStorageMock.getItem('hermes_tracked_tasks') || '[]')

      expect(stored).toEqual(['task-2'])
    })

    it('dispatches custom event after removal', () => {
      taskTracker.addTask('task-1')
      dispatchEventSpy.mockClear()

      taskTracker.removeTask('task-1')

      expect(dispatchEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'taskRemoved',
          detail: expect.objectContaining({
            taskId: 'task-1',
            action: 'removed',
          }),
        })
      )
    })
  })

  describe('getTasks', () => {
    it('returns empty array when no tasks exist', () => {
      expect(taskTracker.getTasks()).toEqual([])
    })

    it('returns all tracked tasks in correct order', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')

      const tasks = taskTracker.getTasks()

      expect(tasks).toEqual(['task-3', 'task-2', 'task-1'])
    })

    it('handles corrupted localStorage data', () => {
      localStorageMock.setItem('hermes_tracked_tasks', 'invalid json')

      // Should return empty array instead of throwing
      expect(() => taskTracker.getTasks()).not.toThrow()
      expect(taskTracker.getTasks()).toEqual([])
    })
  })

  describe('clearTasks', () => {
    it('removes all tasks', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')

      taskTracker.clearTasks()

      expect(taskTracker.getTasks()).toEqual([])
    })

    it('clears localStorage', () => {
      taskTracker.addTask('task-1')
      taskTracker.clearTasks()

      const stored = localStorageMock.getItem('hermes_tracked_tasks')

      expect(stored).toBe(null)
    })
  })

  describe('Order preservation for home page', () => {
    it('ensures newest downloads appear at top of home page task list', () => {
      // Simulate adding downloads over time
      const downloadSequence = [
        'download-morning-1',
        'download-morning-2',
        'download-afternoon-1',
        'download-afternoon-2',
        'download-evening-1',
      ]

      downloadSequence.forEach(id => taskTracker.addTask(id))

      const tasks = taskTracker.getTasks()

      // Most recent download should be first
      expect(tasks[0]).toBe('download-evening-1')
      expect(tasks[tasks.length - 1]).toBe('download-morning-1')
    })

    it('maintains correct order after removing middle task', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')
      taskTracker.addTask('task-4')

      taskTracker.removeTask('task-2')

      const tasks = taskTracker.getTasks()

      expect(tasks).toEqual(['task-4', 'task-3', 'task-1'])
    })

    it('maintains correct order after removing first task', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')

      taskTracker.removeTask('task-3') // Remove newest

      const tasks = taskTracker.getTasks()

      expect(tasks).toEqual(['task-2', 'task-1'])
    })

    it('maintains correct order after removing last task', () => {
      taskTracker.addTask('task-1')
      taskTracker.addTask('task-2')
      taskTracker.addTask('task-3')

      taskTracker.removeTask('task-1') // Remove oldest

      const tasks = taskTracker.getTasks()

      expect(tasks).toEqual(['task-3', 'task-2'])
    })
  })
})
