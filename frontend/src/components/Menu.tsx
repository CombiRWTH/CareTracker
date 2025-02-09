import type { ReactNode } from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { createPortal } from 'react-dom'
import { useOutsideClick } from '@/util/hooks/useOutsideClick'

type PropBag = {
  isOpen: boolean,
  toggleOpen: () => void,
  isDisabled: boolean
}

type MenuProps = {
  children: (bag: PropBag) => ReactNode,
  display: (bag: PropBag) => ReactNode,
  isDisabled?: boolean,
  isClosingOnScroll?: boolean,
  containerClassName?: string,
  menuContainerClassName?: string
}

/**
 * A menu component that is opened via a button
 * @param children The menu items to displays
 * @param display The button to display
 * @param containerClassName  The style overwrite of the container holding all parts including the button
 * @param menuContainerClassName The style overwrite of the menu container
 * @param isDisabled Whether the component should be disabled
 * @param isClosingOnScroll Whether the menu should close when scrolled. (default: true)
 * @constructor
 */
export const Menu = ({
  children,
  display,
  containerClassName,
  menuContainerClassName,
  isDisabled = false,
  isClosingOnScroll = true,
}: MenuProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  useOutsideClick([ref, menuRef], () => setIsOpen(false))
  // const [_, setOffset] = useState({ x: 0, y: 0 })

  const bag: PropBag = {
    isOpen,
    toggleOpen: () => setIsOpen(!isOpen),
    isDisabled
  }

  const boundingRect = ref?.current?.getBoundingClientRect()

  /*
  const calculatePosition = useCallback(() => {
    let scrollTop = 0
    let scrollLeft = 0

    let parent: HTMLElement | null = ref.current

    while (parent) {
      if (parent.scrollTop) scrollTop += parent.scrollTop
      if (parent.scrollLeft) scrollLeft += parent.scrollLeft
      parent = parent.parentElement
    }
    setOffset({ x: scrollLeft, y: scrollTop })
  }, [])
  */

  const onScrollHandler = useCallback(() => {
    if (isClosingOnScroll) {
      setIsOpen(false)
    } else {
      // calculatePosition()
    }
  }, [isClosingOnScroll])

  useEffect(() => {
    if (isOpen) {
      // calculatePosition() // Calculate position initially

      // Add event listeners to recalculate position
      window.addEventListener('scroll', onScrollHandler, true) // Use `true` to capture scroll in bubbling phase
      window.addEventListener('resize', onScrollHandler)

      return () => {
        // Clean up event listeners
        window.removeEventListener('scroll', onScrollHandler, true)
        window.removeEventListener('resize', onScrollHandler)
      }
    }
  }, [isOpen, onScrollHandler])

  return (
    <div ref={ref} className={`relative ${containerClassName}`}>
      {display(bag)}
      {isOpen && (
        createPortal(
          <div
            ref={menuRef}
            className={`absolute shadow-lg z-30 mt-2 flex flex-col gap-y-2 p-2 rounded-md bg-container ${menuContainerClassName} `}
            style={{
              top: (boundingRect?.y ?? 0) + (boundingRect?.height ?? 0),
              left: (boundingRect?.x ?? 0),
              width: boundingRect?.width ?? 'auto'
            }}
          >
            {children(bag)}
          </div>, document.body)
      )}
    </div>
  )
}
