import type { NextPage } from 'next'
import React, { useRef, useState, useEffect } from 'react'
import { Upload, CheckCircle, XCircle, Download, RefreshCw } from 'lucide-react'
import { Page } from '@/layout/Page'
import { Header } from '@/layout/Header'
import { LinkTiles } from '@/components/LinkTiles'
import { useStationsAPI } from '@/api/stations'
import type { AnalysisFrequency } from '@/api/analysis'
import { useAnalysisAPI } from '@/api/analysis'
import { useGraphAPI } from '@/api/graph'
import type { StationMonthly, StationDaily } from '@/util/export'
import { exportMonthlyAnalysis, exportDailyAnalysis } from '@/util/export'
import { apiURL } from '@/config'
import { getCookie } from '@/util/getCookie'
import { ComparisonGraph } from '@/components/GraphPopup'
import { StationTimeGraph } from '@/components/GraphForSingleStation'
import { Menu } from '@/components/Menu'
import { Select } from '@/components/Select'
import { MultiSelect } from '@/components/MultiSelect'
import { Tooltip } from '@/components/Tooltip'

/*
*  Page for the analysis of data
*/
export const AnalysisPage: NextPage = () => {
  // Show daily or monthly data for the stations
  const [viewMode, setViewMode] = useState<AnalysisFrequency>('daily')
  const { stations } = useStationsAPI()
  const { data, reload: refetchAnalysis } = useAnalysisAPI(viewMode)
  const {
    data: graphData,
    reload: refetchGraph
  } = useGraphAPI(viewMode)
  const [selectedStations, setSelectedStations] = useState<number[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [showNotification, setShowNotification] = useState(false)
  const monthlyInputRef = useRef<HTMLInputElement>(null)
  const dailyInputRef = useRef<HTMLInputElement>(null)
  // Refresh counter to trigger refreshes in child components
  const [refreshCounter, setRefreshCounter] = useState(0)

  // Station options for MultiSelect
  const stationOptions = [
    {
      value: -1,
      label: 'Alle Stationen'
    },
    ...stations.map(station => ({
      value: station.id,
      label: station.name
    }))
  ]

  const canExport = selectedStations.length > 0

  // Hide notification for import/export after 10 seconds
  useEffect(() => {
    if (showNotification) {
      const timer = setTimeout(() => {
        setShowNotification(false)
        setError('')
        setSuccess('')
      }, 10000)
      return () => clearTimeout(timer)
    }
  }, [showNotification])

  // Reload all data from the backend
  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([
        refetchAnalysis(),
        refetchGraph()
      ])
      // Increment the refresh counter to trigger refresh in child components
      setRefreshCounter(prev => prev + 1)
      setSuccess('Daten erfolgreich aktualisiert')
      setShowNotification(true)
    } catch (err) {
      setError('Fehler beim Aktualisieren der Daten')
      setShowNotification(true)
    } finally {
      setIsRefreshing(false)
    }
  }

  // Upload excel file to the backend
  // that is used to make the further analysis for the shifts
  const handleFileUpload = async (file: File, type: 'caregiver' | 'patient') => {
    const validExcelTypes = [
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.oasis.opendocument.spreadsheet'
    ]

    if (!validExcelTypes.includes(file.type)) {
      setError('Bitte nur Excel-Dateien hochladen (.xls oder .xlsx)')
      setShowNotification(true)
      return
    }

    setIsUploading(true)
    setError('')
    setSuccess('')

    try {
      const formData = new FormData()
      formData.append(type, file)

      const cookie = getCookie('csrftoken')
      const response = await fetch(`${apiURL}/import/${type}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': cookie ?? '',
        },
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Upload fehlgeschlagen')
      }

      setSuccess(`${type === 'caregiver' ? 'Schichtplan' : 'Patientendaten'} erfolgreich hochgeladen`)

      if (type === 'caregiver' && monthlyInputRef.current) {
        monthlyInputRef.current.value = ''
      } else if (type === 'patient' && dailyInputRef.current) {
        dailyInputRef.current.value = ''
      }

      // Refresh data after successful upload
      await handleRefresh()
    } catch (err) {
      setError('Datei-Upload fehlgeschlagen. Bitte versuchen Sie es erneut.')
    } finally {
      setIsUploading(false)
      setShowNotification(true)
    }
  }

  // Use the hooks to export data for the station in an excel file
  const exportData = async () => {
    // Filter the stations
    let filteredData
    if (selectedStations.includes(-1)) {
      filteredData = data
    } else {
      filteredData = data.filter(station => selectedStations.includes(station.id))
    }

    if (viewMode === 'daily') {
      await exportDailyAnalysis(filteredData as StationDaily[])
    } else {
      await exportMonthlyAnalysis(filteredData as StationMonthly[], viewMode === 'quarterly')
    }
  }

  return (
    <Page
      header={(
        <Header
          className="!justify-start gap-x-8"
          end={(
            <div className="flex justify-end w-full items-center gap-x-6">
              {showNotification && (error || success) && (
                <div
                  className={`flex items-center gap-2 px-3 py-1 rounded ${
                    error ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                  }`}
                >
                  {error ? (
                    <XCircle className="w-4 h-4 text-red-500"/>
                  ) : (
                    <CheckCircle className="w-4 h-4 text-green-500"/>
                  )}
                  <span className="text-sm">{error || success}</span>
                </div>
              )}
              <Tooltip
                tooltip="Daten aktualisieren"
                position="bottom"
                containerClassName="!w-auto"
              >
                <button
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  className={`flex items-center justify-center rounded p-2 ${
                    isRefreshing ? 'bg-gray-200 text-gray-500' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                  }`}
                >
                  <RefreshCw
                    size={24}
                    className={isRefreshing ? 'animate-spin' : ''}
                  />
                </button>
              </Tooltip>
              <input
                ref={monthlyInputRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                id="monthly-upload"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleFileUpload(file, 'caregiver')
                }}
              />
              <Menu
                display={({
                  isDisabled,
                  toggleOpen
                }) => (
                  <button
                    className={`flex flex-row gap-x-2 items-center ${isDisabled ? 'button-full-disabled' : 'button-full-primary'}`}
                    onClick={toggleOpen} disabled={isDisabled}>
                    <Upload size={24}/>
                    Importieren
                  </button>
                )}
                isDisabled={isUploading}
                menuContainerClassName="!bg-gray-100"
              >
                {({ toggleOpen }) => (
                  <>
                    <button
                      onClick={() => {
                        toggleOpen()
                        monthlyInputRef.current?.click()
                      }}
                      disabled={isUploading}
                      className="button-padding bg-gray-200 card-hover whitespace-nowrap"
                    >
                      Schichtplan
                    </button>
                    <button
                      onClick={() => {
                        toggleOpen()
                        dailyInputRef.current?.click()
                      }}
                      disabled={isUploading}
                      className="button-padding bg-gray-200 card-hover whitespace-nowrap"
                    >
                      Patientendaten
                    </button>
                  </>
                )}
              </Menu>
              <input
                ref={dailyInputRef}
                type="file"
                accept=".xlsx,.xls"
                className="hidden"
                id="daily-upload"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleFileUpload(file, 'patient')
                }}
              />
              <Tooltip
                tooltip={!canExport ? 'Stationen müssen vor dem Export durch ausgewählt werden' : 'Ausgewählte Daten exportieren'}
                position="bottom"
                containerClassName="!w-auto"
              >
                <MultiSelect
                  selected={selectedStations}
                  onChange={(stations) => {
                    setSelectedStations(stations)
                    if (stations.length > 0) {
                      exportData()
                    }
                  }}
                  items={stationOptions}
                  noneLabel="Exportieren"
                  icon={<Download size={24}/>}
                />
              </Tooltip>

              <Select<AnalysisFrequency>
                buttonClassName="!min-w-[150px]"
                selected={viewMode}
                items={[{
                  value: 'daily',
                  label: 'Täglich',
                },
                {
                  value: 'monthly',
                  label: 'Monatlich',
                },
                {
                  value: 'quarterly',
                  label: 'Quartalsweise',
                }]}
                onChange={value => setViewMode(value)}
              />
            </div>
          )}
        >
          <div className="bg-gray-200 w-1 h-10 rounded"/>
          <LinkTiles links={[{
            name: 'Stationen',
            url: '/stations'
          }, {
            name: 'Analyse',
            url: '/analysis'
          }]}/>
        </Header>
      )}
    >
      <div className="flex flex-col w-full p-10 gap-y-4 content-start">
        <div className="p-4">
          <div className="bg-white rounded-xl shadow-md p-6">
            <ComparisonGraph data={graphData} />
          </div>
        </div>
        <div className="p-4">
          <div className="bg-white rounded-xl shadow-md p-6">
            <StationTimeGraph
              viewMode={viewMode}
              stations={stations}
              refreshTrigger={refreshCounter}
            />
          </div>
        </div>
      </div>
    </Page>
  )
}

export default AnalysisPage
