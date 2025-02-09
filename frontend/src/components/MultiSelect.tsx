import React from 'react'
import { ChevronDown, ChevronUp, Check } from 'lucide-react'
import { noop } from '@/util/noop'
import { Menu } from '@/components/Menu'

export type SelectItem<T> = {
  value: T,
  label: string
}

type MultiSelectProps<T> = {
  selected: T[],
  onChange?: (value: T[]) => void,
  items: SelectItem<T>[],
  isDisabled?: boolean,
  containerClassName?: string,
  menuContainerClassName?: string,
  buttonClassName?: string,
  noneLabel?: string,
  icon?: React.ReactNode
}

/**
 * A Multi-Select component that allows selecting multiple items
 * @param items The items to select from
 * @param selected The chosen items
 * @param onChange The callback when the user changes the value
 * @param buttonClassName The style overwrite of the button
 * @param noneLabel The label when no value is selected
 * @param props Additional props for the component
 * @constructor
 */
export const MultiSelect = <T, >({
  items,
  selected,
  onChange = noop,
  buttonClassName,
  noneLabel,
  icon,
  ...props
}: MultiSelectProps<T>) => {
  const selectedItemsLabel = selected.length === 0
    ? (noneLabel ?? 'Nichts ausgewählt')
    : selected.length === 1
      ? items.find(item => item.value === selected[0])?.label ?? ''
      : `${selected.length} ausgewählt`

  return (
    <Menu {...props} display={({
      isOpen,
      toggleOpen,
      isDisabled
    }) => (
      <button
        onClick={toggleOpen}
        disabled={isDisabled}
        className={`relative flex flex-row justify-between gap-x-2 min-w-[120px] ${isDisabled ? 'button-full-disabled' : 'button-full-primary'} ${buttonClassName}`}
      >
        {icon && icon}
        {selectedItemsLabel}
        {isOpen ? <ChevronUp size={24}/> : <ChevronDown size={24}/>}
      </button>
    )}>
      {() => items.map((item, index) => (
        <button
          key={index}
          onClick={() => {
            const isCurrentlySelected = selected.includes(item.value)
            const newSelection = isCurrentlySelected
              ? selected.filter(selectedItem => selectedItem !== item.value)
              : [...selected, item.value]

            onChange(newSelection)
          }}
          className="button-padding bg-gray-200 card-hover whitespace-nowrap flex items-center justify-between"
        >
          <span>{item.label}</span>
          {selected.includes(item.value) && <Check size={20} className="text-green-500"/>}
        </button>
      ))}
    </Menu>
  )
}
