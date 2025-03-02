import { useCallback, useEffect, useState } from 'react'
import { apiURL } from '@/config'
import { formatDateBackend } from '@/util/date'
import type { AnalysisFrequency } from '@/api/analysis'

const getStartDate = (viewMode: AnalysisFrequency) => {
  const startDate = new Date()

  switch (viewMode) {
    case 'daily':
      break
    case 'monthly':
      // Go back one month from the current date
      startDate.setMonth(startDate.getMonth() - 1)
      break
    case 'quarterly':
      // Go back three months from the current date
      startDate.setMonth(startDate.getMonth() - 3)
      break
  }

  return formatDateBackend(startDate)
}

/**
 * Hook to load the analysis data for caregivers for all stations
 */
export const useGraphAPI = (viewMode: AnalysisFrequency) => {
  const [data, setData] = useState<any[]>([])
  const [date, setDate] = useState<Date>(new Date())

  const fetchData = useCallback(async () => {
    try {
      const formattedDate = formatDateBackend(date)
      const formattedStartDate = getStartDate(viewMode)

      const response = await fetch(`${apiURL}/analysis/caregivers/${formattedStartDate}/${formattedDate}/`)
      const data = await response.json()
      setData(data)
    } catch (error) {
      console.error('Failed to fetch graph data:', error)
    }
  }, [date, viewMode])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    data,
    date,
    setDate,
    reload: fetchData
  }
}

// Define the common structure for each dataset entry
interface DatasetEntry {
  date: string,
  should: number | null,
  is: number
}

// Define the main data structure
interface Data {
  station_id: number,
  station_name: string,
  dataset_night: DatasetEntry[],
  dataset_day: DatasetEntry[]
}

/**
 * Hook to load the analysis data for caregivers for one station
 */
export const useGraphAPIForStation = (viewMode: AnalysisFrequency, stationID: number) => {
  const [data, setData] = useState<Data | null>(null)
  const [date, setDate] = useState<Date>(new Date())

  const fetchData = useCallback(async () => {
    try {
      if (stationID === -1) {
        return
      }
      const formattedDate = formatDateBackend(date)
      const formattedStartDate = getStartDate(viewMode)

      const response = await fetch(`${apiURL}/analysis/caregivers/${stationID}/${formattedStartDate}/${formattedDate}/`)
      const data = await response.json()
      setData(data)
    } catch (error) {
      console.error('Failed to fetch graph data:', error)
    }
  }, [date, viewMode, stationID])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    data,
    date,
    setDate,
    reload: fetchData
  }
}
