import { useState, useCallback } from 'react'

export interface FormatOption {
  value: string
  label: string
  description: string
  quality?: string
  size?: string
  disabled?: boolean
}

interface UseFormatSelectionOptions {
  initialFormat?: string
  formats?: FormatOption[]
  onFormatChange?: (format: string) => void
}

const defaultFormats: FormatOption[] = [
  {
    value: 'best',
    label: 'Best Quality',
    description: 'Highest available quality for both video and audio'
  },
  {
    value: 'worst',
    label: 'Lowest Quality',
    description: 'Smallest file size, lower quality'
  },
  {
    value: 'bestvideo+bestaudio',
    label: 'Best Video + Audio',
    description: 'Separate video and audio streams merged together'
  },
  {
    value: 'bestaudio',
    label: 'Audio Only',
    description: 'Download only the audio track'
  }
]

export function useFormatSelection(options: UseFormatSelectionOptions = {}) {
  const {
    initialFormat = 'best',
    formats = defaultFormats,
    onFormatChange
  } = options

  const [selectedFormat, setSelectedFormat] = useState<string>(initialFormat)

  const selectFormat = useCallback((format: string) => {
    setSelectedFormat(format)
    onFormatChange?.(format)
  }, [onFormatChange])

  const getSelectedFormatOption = useCallback(() => {
    return formats.find(format => format.value === selectedFormat)
  }, [formats, selectedFormat])

  const getFormatOptions = useCallback(() => {
    return formats
  }, [formats])

  return {
    selectedFormat,
    selectFormat,
    selectedOption: getSelectedFormatOption(),
    options: getFormatOptions(),
  }
}


