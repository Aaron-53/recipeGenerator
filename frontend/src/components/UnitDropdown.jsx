import React, { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { FiChevronDown } from 'react-icons/fi'

const UNITS_BY_CATEGORY = [
  {
    category: 'Count',
    units: [
      'no.',
      'piece',
      'pcs',
      'slice',
      'clove',
      'head',
      'bunch',
      'stalk',
      'sprig',
      'leaf',
      'cube',
      'pinch',
      'dash',
      'whole',
      'half',
      'dozen',
      'count',
      'item',
      'serving',
    ],
  },
  {
    category: 'Volume (Liquid)',
    units: [
      'ml',
      'mL',
      'L',
      'liter',
      'litre',
      'cl',
      'dl',
      'fl oz',
      'fluid ounce',
      'cup',
      'tablespoon',
      'tbsp',
      'teaspoon',
      'tsp',
      'pint',
      'pt',
      'quart',
      'qt',
      'gallon',
      'gal',
      'drop',
      'dash',
      'shot',
      'jigger',
    ],
  },
  {
    category: 'Mass / Weight',
    units: [
      'g',
      'gram',
      'grams',
      'kg',
      'kilogram',
      'mg',
      'oz',
      'ounce',
      'lb',
      'pound',
      'lbs',
    ],
  },
  {
    category: 'Volume (Dry / Cooking)',
    units: [
      'cup',
      'tablespoon',
      'tbsp',
      'teaspoon',
      'tsp',
      'heaped tbsp',
      'level tbsp',
      'scant cup',
    ],
  },
  {
    category: 'Container / Other',
    units: [
      'can',
      'jar',
      'packet',
      'bag',
      'box',
      'bottle',
      'strip',
      'sheet',
      'pack',
      'carton',
      'tin',
      'sachet',
      'envelope',
    ],
  },
]

const allUnits = UNITS_BY_CATEGORY.flatMap(({ units }) => units)

const filterByQuery = (query) => {
  const q = query.trim().toLowerCase()
  if (!q) return UNITS_BY_CATEGORY
  return UNITS_BY_CATEGORY.map(({ category, units }) => ({
    category,
    units: units.filter((u) => u.toLowerCase().includes(q)),
  })).filter(({ units }) => units.length > 0)
}

const DROPDOWN_MAX_HEIGHT = 260
const SPACE_BUFFER = 16

const UnitDropdown = ({ value, onChange, placeholder = 'e.g. no, ml, g', id, className = '' }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [openUpward, setOpenUpward] = useState(false)
  const containerRef = useRef(null)

  const filtered = filterByQuery(searchQuery)
  const displayValue = value || ''

  useLayoutEffect(() => {
    if (!isOpen || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const spaceBelow = window.innerHeight - rect.bottom
    const spaceAbove = rect.top
    setOpenUpward(spaceBelow < DROPDOWN_MAX_HEIGHT + SPACE_BUFFER && spaceAbove > spaceBelow)
  }, [isOpen])

  useEffect(() => {
    if (!isOpen) return
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  const handleSelect = (unit) => {
    onChange(unit)
    setIsOpen(false)
    setSearchQuery('')
  }

  const handleToggle = () => {
    if (!isOpen) {
      setSearchQuery('')
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const spaceBelow = window.innerHeight - rect.bottom
        const spaceAbove = rect.top
        setOpenUpward(
          spaceBelow < DROPDOWN_MAX_HEIGHT + SPACE_BUFFER && spaceAbove > spaceBelow
        )
      }
      setIsOpen(true)
    } else {
      setIsOpen(false)
    }
  }

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value)
    if (!isOpen) setIsOpen(true)
  }

  const handleSearchKeyDown = (e) => {
    if (e.key === 'Escape') {
      setIsOpen(false)
      e.target.blur()
    }
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        role='combobox'
        aria-expanded={isOpen}
        aria-haspopup='listbox'
        aria-controls='unit-listbox'
        aria-label='Unit'
        id={id}
        onClick={handleToggle}
        className='w-full px-4 py-1.5 rounded-full border border-[#f2cec2]/80 text-[#4a4a4a] placeholder-[#4a4a4a]/60 focus:outline-none focus:ring-2 focus:ring-[#F6C7B7]/50 flex items-center justify-between cursor-pointer bg- min-h-[34px]'
      >
        <span className={displayValue ? 'text-[#4a4a4a]' : 'text-[#4a4a4a]/60'}>
          {displayValue || placeholder}
        </span>
        <FiChevronDown
          size={18}
          className={`text-[#5C6E43] shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </div>

      {isOpen && (
        <div
          id='unit-listbox'
          role='listbox'
          className={`absolute z-30 left-0 right-0 rounded-xl border border-[#e8d5d0]/80 bg-[#F6E7C8] shadow-lg max-h-[260px] overflow-hidden flex flex-col ${
            openUpward ? 'bottom-full mb-1' : 'top-full mt-1'
          }`}
        >
          <div className='p-2 border-b border-[#e8d5d0]/60 shrink-0'>
            <input
              type='text'
              value={searchQuery}
              onChange={handleSearchChange}
              onKeyDown={handleSearchKeyDown}
              placeholder='Search units...'
              className='w-full px-3 py-2 rounded-lg border border-[#f2cec2]/80 text-[#4a4a4a] placeholder-[#4a4a4a]/60 focus:outline-none focus:ring-2 focus:ring-[#F6C7B7]/50 text-sm'
              autoFocus
              aria-label='Search units'
            />
          </div>
          <div className='inventory-rows-scroll overflow-y-auto overscroll-contain max-h-[200px]'>
            {filtered.length === 0 ? (
              <div className='px-4 py-3 text-sm text-[#4a4a4a]/70'>No units match your search.</div>
            ) : (
              filtered.map(({ category, units }) => (
                <div key={category} className='py-1'>
                  <div className='px-3 py-1.5 text-xs font-semibold text-[#5C6E43]/80 uppercase tracking-wide'>
                    {category}
                  </div>
                  {units.map((unit) => (
                    <button
                      key={unit}
                      type='button'
                      role='option'
                      aria-selected={value === unit}
                      onClick={() => handleSelect(unit)}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-[#ead8b6]/50 transition-colors cursor-pointer ${
                        value === unit ? 'bg-[#ead8b6]/70 text-[#5C6E43]' : 'text-[#4a4a4a]'
                      }`}
                    >
                      {unit}
                    </button>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default UnitDropdown
export { UNITS_BY_CATEGORY, allUnits }
