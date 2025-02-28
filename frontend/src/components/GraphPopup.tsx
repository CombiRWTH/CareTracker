import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  Tooltip,
  ResponsiveContainer
} from 'recharts'
import type { CurveType } from 'recharts/types/shape/Curve'

interface ComparisonGraphProps {
  data: any[]
}

/*
  The ComparisonGraph component is a popup that displays a comparison graph of the data provided.
  It uses the recharts library to display the data in a line chart. The data is processed to
  display the day and night data for each station in the provided data.
*/
export const ComparisonGraph = ({ data }: ComparisonGraphProps) => {
  const processedData = data.reduce((acc: any, station: any) => {
    const stationData = {
      dayData: station.dataset_day[0] || {
        is: 0,
        should: 0
      },
      nightData: station.dataset_night[0] || {
        is: 0,
        should: 0
      }
    }

    return [
      ...acc,
      {
        name: station.station_name,
        dayIs: stationData.dayData.is || 0,
        dayShould: stationData.dayData.should || 0,
        nightIs: stationData.nightData.is || 0,
        nightShould: stationData.nightData.should || 0
      }
    ]
  }, [])

  // Calculate statistics
  const findMin = (key: 'dayIs' | 'nightIs') => {
    const minEntry = processedData.reduce((min: any, curr: any) =>
      curr[key] < min.value ? { value: curr[key], station: curr.name } : min,
    { value: Infinity, station: '' }
    )
    return {
      value: minEntry.value.toFixed(2),
      station: minEntry.station
    }
  }

  const calculateAvg = (key: 'dayIs' | 'nightIs') => {
    const sum = processedData.reduce((acc: any, curr: any) => acc + curr[key], 0)
    return (sum / processedData.length).toFixed(2)
  }

  // Define common line properties
  const baseLineProps = {
    type: 'monotone' as CurveType,
    dot: { r: 4 },
    activeDot: { r: 7 },
    strokeWidth: 4,
  }

  // Colors for Ist and Soll
  const colors = {
    night: '#8884d8', // Purple for "Ist"
    day: '#82ca9d' // Green for "Soll"
  }

  return (
    <div className="flex gap-4">
      <div className="flex-1">
        <h2 className="text-xl font-bold mb-4">{'Pflegekräfte: Ist- vs. Soll-Werte'}</h2>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={processedData}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5
              }}
            >
              <CartesianGrid strokeDasharray="3 3"/>
              <XAxis
                dataKey="name"
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis/>
              <Tooltip/>
              <Legend/>
              <Line
                {...baseLineProps}
                dataKey="dayIs"
                name="Tag (Ist)"
                stroke={colors.day}
                strokeWidth={3}
                legendType="plainline"
              />
              <Line
                {...baseLineProps}
                dataKey="dayShould"
                name="Tag (Soll)"
                stroke={colors.day}
                strokeDasharray="5 5"
                strokeWidth={3}
                legendType="plainline"
              />
              <Line
                {...baseLineProps}
                dataKey="nightIs"
                name="Nacht (Ist)"
                stroke={colors.night}
                strokeWidth={3}
                legendType="plainline"
              />
              <Line
                {...baseLineProps}
                dataKey="nightShould"
                name="Nacht (Soll)"
                stroke={colors.night}
                strokeDasharray="5 5"
                strokeWidth={3}
                legendType="plainline"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="w-72 bg-white rounded-lg shadow-sm p-4">
        <h3 className="font-medium mb-4 text-base">Statistik Übersicht</h3>
        <table className="w-full">
          <tbody className="text-sm">
            <tr className="border-b">
              <td className="py-2">Min Tag (Ist)</td>
              <td className="text-right">
                {findMin('dayIs').value}
                <div className="text-xs text-gray-500">({findMin('dayIs').station})</div>
              </td>
            </tr>
            <tr className="border-b">
              <td className="py-2">Min Nacht (Ist)</td>
              <td className="text-right">
                {findMin('nightIs').value}
                <div className="text-xs text-gray-500">({findMin('nightIs').station})</div>
              </td>
            </tr>
            <tr className="border-b">
              <td className="py-2">∅ Tag (Ist)</td>
              <td className="text-right">{calculateAvg('dayIs')}</td>
            </tr>
            <tr>
              <td className="py-2">∅ Nacht (Ist)</td>
              <td className="text-right">{calculateAvg('nightIs')}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default ComparisonGraph
