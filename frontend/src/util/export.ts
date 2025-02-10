import ExcelJS from 'exceljs'
import { formatDateFull } from '@/util/date'

/**
 * Data type for Station daily data
 */
export type StationDaily = {
  /** The identifier of the Station */
  id: number,
  /** The name of the Station */
  name: string,
  /** The minutes of work for the Station */
  minutes: number
}

/**
 * Data type for Station monthly data
 */
export type StationMonthly = {
  /** The identifier of the Station */
  id: number,
  /** The name of the Station */
  name: string,
  /**
   * The monthly date by date
   */
  data: { day: number, minutes: number }[],
  /**
   * Sum of all minutes
   */
  sum: number
}

/**
 * Saves the data to an Excel file
 * @param buffer The data to save
 * @param fileName The file name to use
 */
export const saveAsExcelFile = (buffer: ArrayBuffer, fileName: string): void => {
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()

  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Exports the daily Station data to an Excel file
 * @param stations The stations to use
 */
export const exportDailyAnalysis = async (stations: StationDaily[]): Promise<void> => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('Analyse')

  worksheet.columns = [
    {
      header: 'ID',
      key: 'id',
      width: 10
    },
    {
      header: 'Name',
      key: 'name',
      width: 30
    },
    {
      header: 'Minuten',
      key: 'minutes',
      width: 15
    }
  ]

  const totalSum = stations.reduce((total, station) => total + station.minutes, 0)

  stations.forEach((station) => {
    worksheet.addRow({
      id: station.id,
      name: station.name,
      minutes: station.minutes
    })
  })

  const totalRow = worksheet.addRow({
    id: -1,
    name: 'Gesamt',
    minutes: totalSum
  })

  totalRow.eachCell((cell) => {
    cell.font = {
      bold: true,
      color: { argb: 'FFFFFFFF' }
    }
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF000000' }
    }
  })

  const buffer = await workbook.xlsx.writeBuffer()
  saveAsExcelFile(buffer, `${formatDateFull(new Date())}_Tägliche_Analyse.xlsx`)
}

/**
 * Exports the monthly Station data to an Excel file
 * @param stations The stations to use
 * @param isQuarterly Name of the exported analysis - 'Quartalsweise' or 'Monatliche'
 */
export const exportMonthlyAnalysis = async (stations: StationMonthly[], isQuarterly: boolean): Promise<void> => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('Analyse')

  worksheet.columns = [
    {
      header: 'ID',
      key: 'id',
      width: 10
    },
    {
      header: 'Name',
      key: 'name',
      width: 30
    },
    {
      header: 'Tag',
      key: 'day',
      width: 10
    },
    {
      header: 'Minuten',
      key: 'minutes',
      width: 15
    }
  ]

  const totalSum = stations.reduce((total, station) => total + station.sum, 0)

  stations.forEach((station) => {
    station.data.forEach((dayData) => {
      worksheet.addRow({
        id: station.id,
        name: station.name,
        day: dayData.day,
        minutes: dayData.minutes
      })
    })

    const summaryRow = worksheet.addRow({
      id: station.id,
      name: `${station.name} - Summe`,
      day: '',
      minutes: station.sum
    })

    summaryRow.eachCell((cell) => {
      cell.font = { bold: true }
      cell.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FFEEEEEE' }
      }
    })

    worksheet.addRow({})
  })

  const totalRow = worksheet.addRow({
    id: -1,
    name: 'Gesamt',
    day: '',
    minutes: totalSum
  })

  totalRow.eachCell((cell) => {
    cell.font = {
      bold: true,
      color: { argb: 'FFFFFFFF' }
    }
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FF000000' }
    }
  })

  // Generate the Excel file and trigger download
  const buffer = await workbook.xlsx.writeBuffer()
  saveAsExcelFile(
    buffer,
    `${formatDateFull(new Date())}_${isQuarterly ? 'Quartalsweise' : 'Monatliche'}_Analyse.xlsx`
  );

}
