import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  ResponsiveContainer
} from 'recharts'
import type { CurveType } from 'recharts/types/shape/Curve'
import type { AnalysisFrequency } from '@/api/analysis'
import type { Station } from '@/data-models/station'
import { Select } from '@/components/Select'
import { useGraphAPIForStation } from '@/api/graph'

interface StationTimeGraphProps {
  viewMode: AnalysisFrequency,
  stations: Station[]
}

export const StationTimeGraph = ({ viewMode, stations }: StationTimeGraphProps) => {
  const [selectedStation, setSelectedStation] = React.useState<number>()
  const {
    data,
  } = useGraphAPIForStation(viewMode, selectedStation ?? -1)

  const stationOptions = stations.map(station => ({
    value: station.id,
    label: station.name
  }))

  let processedData: any
  if (data !== null) {
    processedData = data.dataset_day.map((dayData, index) => {
      const nightData = data.dataset_night[index] || { is: 0, should: 0 }
      return {
        displayDate: new Date(dayData.date).getDate().toString(),
        dayIs: dayData.is || 0,
        dayShould: dayData.should || 0,
        nightIs: nightData.is || 0,
        nightShould: nightData.should || 0
      }
    })
  }

  // Calculate statistics
  const calculateStats = (dataset: typeof processedData) => {
    if (dataset === undefined) {
      return {
        minDay: 0,
        minNight: 0,
        avgDay: 0,
        avgNight: 0
      }
    }
    const minDay = Math.min(...dataset.map((d: any) => d.dayIs))
    const minNight = Math.min(...dataset.map((d: any) => d.nightIs))
    const avgDay = dataset.reduce((sum: any, curr: any) => sum + curr.dayIs, 0) / dataset.length
    const avgNight = dataset.reduce((sum: any, curr: any) => sum + curr.nightIs, 0) / dataset.length

    return {
      minDay: minDay.toFixed(2),
      minNight: minNight.toFixed(2),
      avgDay: avgDay.toFixed(2),
      avgNight: avgNight.toFixed(2)
    }
  }

  const stats = calculateStats(processedData)

  const baseLineProps = {
    type: 'monotone' as CurveType,
    dot: { r: 4 },
    activeDot: { r: 7 },
    strokeWidth: 4,
  }

  const colors = {
    night: '#8884d8',
    day: '#82ca9d'
  }

  return (
    <div className="flex gap-4">
      <div className="flex-1">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">{`Pflegekräfte: ${data ? data.station_name : '--'}`}</h2>
          <Select<number>
            selected={selectedStation}
            items={stationOptions}
            onChange={setSelectedStation}
            noneLabel="Station auswählen"
          />
        </div>
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
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="displayDate"
                tickLine={false}
                label={{
                  value: 'Tag',
                  position: 'outsideBottom',
                  offset: 20,
                  dy: 10
                }}
              />
              <YAxis />
              <Legend />
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
              <td className="text-right">{stats.minDay}</td>
            </tr>
            <tr className="border-b">
              <td className="py-2">Min Nacht (Ist)</td>
              <td className="text-right">{stats.minNight}</td>
            </tr>
            <tr className="border-b">
              <td className="py-2">∅ Tag (Ist)</td>
              <td className="text-right">{stats.avgDay}</td>
            </tr>
            <tr>
              <td className="py-2">∅ Nacht (Ist)</td>
              <td className="text-right">{stats.avgNight}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default StationTimeGraph
