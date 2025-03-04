import React, { useEffect, useRef, useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { noop } from '@/util/noop'
import type { DatePickerProps } from '@/components/DatePicker/DatePicker'
import { DatePicker } from '@/components/DatePicker/DatePicker'
import { formatDateVisual } from '@/util/date'
import { tailwindCombine } from '@/util/tailwind'
import { useOutsideClick } from '@/util/hooks/useOutsideClick'

export type DatePickerButtonProps = Omit<DatePickerProps, 'yearMonth'> & {
  /**
   * The date that determines the year and month that are displayed first
   */
  date: Date
}

/**
 * A component for picking a date while showing days of a month with events
 */
export const DatePickerButton = ({
  date = new Date(),
  onDateClick = noop,
  className = '',
  ...restProps
}: DatePickerButtonProps) => {
  const [currentDate, setCurrentDate] = useState<Date>(date)
  const [isOpen, setIsOpen] = useState<boolean>(false)
  const ref = useRef<HTMLDivElement>(null)

  useOutsideClick([ref], () => setIsOpen(false))
  useEffect(() => { setCurrentDate(date) }, [date])

  const triangleSize = 6
  return (
    <div className={tailwindCombine('relative', className)} ref={ref}>
      <button onClick={() => setIsOpen(!isOpen)} className="flex flex-row gap-x-2 items-center">
        <span className="font-bold text-3xl">{formatDateVisual(currentDate)}</span>
        <CalendarDays size={28}/>
      </button>
      {isOpen && (
        <div
          className="absolute z-50 bg-gray-50 px-3 py-2 rounded-xl shadow-lg top-full left-1/2 -translate-x-1/2 mt-2"
          style={{ width: '600px' }}>
          <DatePicker
            yearMonth={date}
            {...restProps}
            onDateClick={(events, selectedDate) => {
              setCurrentDate(selectedDate)
              setIsOpen(false)
              onDateClick(events, selectedDate)
            }}
          />
          <div
            className="absolute w-0 h-0 z-10 bottom-full left-1/2 -translate-x-1/2 border-b-container border-l-transparent border-r-transparent"
            style={{ borderWidth: `0 ${triangleSize}px ${triangleSize}px ${triangleSize}px` }}
          />
        </div>
      )}
    </div>
  )
}
