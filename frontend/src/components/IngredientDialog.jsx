import React, { useState, useEffect } from 'react'
import { FiX } from 'react-icons/fi'
import UnitDropdown from './UnitDropdown'

const defaultValues = { ingredient: '', quantity: '', unit: '' }

const IngredientDialog = ({
  open,
  onClose,
  title,
  submitLabel = 'Add',
  initialValues = defaultValues,
  onSubmit,
  onDelete,
}) => {
  const [ingredient, setIngredient] = useState(initialValues.ingredient ?? '')
  const [quantity, setQuantity] = useState(String(initialValues.quantity ?? ''))
  const [unit, setUnit] = useState(initialValues.unit ?? '')

  useEffect(() => {
    if (open) {
      setIngredient(initialValues.ingredient ?? '')
      setQuantity(String(initialValues.quantity ?? ''))
      setUnit(initialValues.unit ?? '')
    }
  }, [open, initialValues.ingredient, initialValues.quantity, initialValues.unit])

  useEffect(() => {
    if (!open) return
    const onEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onEscape)
    return () => document.removeEventListener('keydown', onEscape)
  }, [open, onClose])

  const handleSubmit = (e) => {
    e?.preventDefault()
    onSubmit({ ingredient, quantity, unit })
    onClose()
  }

  if (!open) return null

  return (
    <div
      className='fixed inset-0 z-20 flex items-center justify-center p-4 bg-black/50'
      onClick={onClose}
      role='dialog'
      aria-modal='true'
      aria-labelledby='ingredient-dialog-title'
    >
      <div
        className='rounded-2xl bg-[#F6E7C8] shadow-xl border border-[#e8d5d0]/60 w-full max-w-md p-4 relative'
        onClick={(e) => e.stopPropagation()}
      >
        <div className='flex items-start justify-between gap-4 mb-4'>
          <h2
            id='ingredient-dialog-title'
            className='text-[#5C6E43] text-xl font-semibold'
          >
            {title}
          </h2>
          <button
            type='button'
            onClick={onClose}
            className='p-1.5 rounded-lg text-[#5C6E43] hover:text-[#475434] transition-colors cursor-pointer shrink-0 -mt-2.5 -mr-2.5'
            aria-label='Close'
          >
            <FiX size={22} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className='flex flex-col gap-3'>
          <div>
            <label htmlFor='dialog-ingredient' className='block text-[#5C6E43] text-sm font-medium mb-1'>
              Ingredient
            </label>
            <input
              id='dialog-ingredient'
              type='text'
              value={ingredient}
              onChange={(e) => setIngredient(e.target.value)}
              placeholder='e.g. Egg'
              className='w-full px-4 py-1.5 rounded-full border border-[#f2cec2]/80 text-[#4a4a4a] placeholder-[#4a4a4a]/60 focus:outline-none focus:ring-2 focus:ring-[#F6C7B7]/50'
            />
          </div>
          <div>
            <label htmlFor='dialog-quantity' className='block text-[#5C6E43] text-sm font-medium mb-1.5'>
              Quantity
            </label>
            <input
              id='dialog-quantity'
              type='number'
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder='e.g. 2'
              className='w-full px-4 py-1.5 rounded-full border border-[#f2cec2]/80 text-[#4a4a4a] placeholder-[#4a4a4a]/60 focus:outline-none focus:ring-2 focus:ring-[#F6C7B7]/50'
            />
          </div>
          <div>
            <label htmlFor='dialog-unit' className='block text-[#5C6E43] text-sm font-medium mb-1.5'>
              Unit
            </label>
            <UnitDropdown
              id='dialog-unit'
              value={unit}
              onChange={setUnit}
              placeholder='e.g. no, ml, g'
            />
          </div>
          <div className='flex gap-3 mt-2'>
            <button
              type='button'
              onClick={onDelete ? () => { onDelete(); onClose(); } : onClose}
              className={`flex-1 py-1.5 rounded-xl font-medium transition-colors cursor-pointer ${
                onDelete
                  ? 'border border-red-300/80 text-red-700 hover:bg-red-100/50'
                  : 'border border-[#f2cec2]/80 text-[#5C6E43] hover:text-[#475434]'
              }`}
            >
              {onDelete ? 'Delete' : 'Cancel'}
            </button>
            <button
              type='submit'
              disabled={!ingredient.trim() || !quantity.trim() || !unit.trim()}
              className='flex-1 py-1.5 rounded-xl bg-[#F6C7B7] text-black/80 font-semibold hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-90 disabled:cursor-not-allowed disabled:hover:opacity-90'
            >
              {submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default IngredientDialog
