import React, { useState, useEffect } from 'react'
import { FiPlus } from 'react-icons/fi'
import { FaRegEdit } from 'react-icons/fa'
import { IoArrowUp } from 'react-icons/io5'
import Navbar from '../components/Navbar'
import ErrorBanner from '../components/ErrorBanner'
import Loader, { LoaderSpinner } from '../components/Loader'
import IngredientDialog from '../components/IngredientDialog'
import { inventoryAPI } from '../services/api'
import { formatApiError } from '../utils/formatApiError'
import { useBodyScrollLock } from '../hooks/useBodyScrollLock'
import inventoryBg from '../assets/inventory.svg'

const Inventory = () => {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [quickInput, setQuickInput] = useState('')
  const [quickSubmitting, setQuickSubmitting] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState(null)

  const loadItems = async () => {
    try {
      setError('')
      const res = await inventoryAPI.getAllItems()
      setItems(res.data || [])
    } catch (err) {
      setError(formatApiError(err, 'Failed to load inventory'))
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadItems()
  }, [])

  useBodyScrollLock(quickSubmitting)

  const openAddDialog = () => {
    setEditingItem(null)
    setDialogOpen(true)
  }

  const openEditDialog = (item) => {
    setEditingItem(item)
    setDialogOpen(true)
  }

  const closeDialog = () => {
    setDialogOpen(false)
    setEditingItem(null)
  }

  const getDialogInitialValues = () => {
    if (!editingItem) return { ingredient: '', quantity: '', unit: '' }
    return {
      ingredient: editingItem.name ?? '',
      quantity: String(editingItem.quantity ?? ''),
      unit: editingItem.unit ?? '',
    }
  }

  const handleDialogSubmit = async ({ ingredient, quantity, unit }) => {
    const payload = {
      name: ingredient.trim(),
      quantity: parseFloat(quantity) || 0,
      unit: (unit || '').trim(),
    }
    if (!payload.name || payload.quantity <= 0 || !payload.unit) return

    try {
      if (editingItem) {
        await inventoryAPI.updateItem(editingItem.item_id, payload)
      } else {
        await inventoryAPI.createItem(payload)
      }
      closeDialog()
      await loadItems()
    } catch (err) {
      const msg = formatApiError(err, 'Failed to save')
      setError(msg)
    }
  }

  const handleDeleteIngredient = async () => {
    if (!editingItem) return
    try {
      await inventoryAPI.deleteItem(editingItem.item_id)
      closeDialog()
      await loadItems()
    } catch (err) {
      setError(formatApiError(err, 'Failed to delete'))
    }
  }

  const handleQuickSubmit = async (e) => {
    e?.preventDefault()
    if (quickSubmitting) return
    const text = quickInput.trim()
    if (!text) return

    try {
      setQuickSubmitting(true)
      setError('')
      const res = await inventoryAPI.parseQuickInput(text)
      if (res?.status === 200) {
        setQuickInput('')
        await loadItems()
      }
    } catch (err) {
      setError(formatApiError(err, 'Failed to parse inventory input'))
    } finally {
      setQuickSubmitting(false)
    }
  }

  return (
    <div className='relative flex min-h-screen flex-col bg-[#5b6d44]'>
      <div
        aria-hidden
        className='pointer-events-none absolute inset-0 z-0 bg-[#5b6d44] bg-cover bg-center bg-no-repeat'
        style={{ backgroundImage: `url(${inventoryBg})` }}
      />
      <div className='relative z-10'>
        <Navbar />
      </div>
      <main className='relative z-10 flex min-h-0 flex-1 flex-col'>
        <div className='relative flex min-h-[calc(100vh-12rem)] flex-1 flex-col overflow-x-hidden'>
          <div className='flex flex-1 items-center justify-center'>
            <div className='w-full w-[calc(100vw-16rem)] px-6 md:px-24 lg:px-52'>
            <h1 className='lg:hidden px-2 pt-2 py-12 text-2xl font-semibold tracking-tight text-[#F2CEC2] sm:text-3xl'>
              Edit Inventory
            </h1>
          <ErrorBanner
            message={error}
            onDismiss={() => setError('')}
            variant="auth"
            className="mb-4 px-4"
          />

          {loading ? (
            <Loader className="min-h-[min(60vh,28rem)] py-0" />
          ) : (
            <>
              <div className='relative rounded-xl bg-[#F6E7C8] overflow-hidden shadow-sm flex flex-col h-[calc(100vh-16rem)]'>
                <table className='w-full border-collapse table-fixed shrink-0'>
                  <thead>
                    <tr className='bg-[#F6C7B7]'>
                      <th className='text-left text-[#5C6E43] font-semibold py-3 px-4 text-base md:text-lg w-[45%]'>
                        Ingredient
                      </th>
                      <th className='text-center text-[#5C6E43] font-semibold py-3 px-4 text-base md:text-lg w-[25%]'>
                        Quantity
                      </th>
                      <th className='text-right text-[#5C6E43] font-semibold py-3 px-4 text-base md:text-lg w-[30%]'>
                        Unit
                      </th>
                    </tr>
                  </thead>
                </table>
                <div className='inventory-rows-scroll overflow-auto min-h-0 flex-1 pb-10'>
                  <table className='w-full border-collapse table-fixed'>
                    <tbody>
                      {items.length === 0 ? (
                        <tr>
                          <td colSpan={3} className='py-8 px-4 text-center text-[#4a4a4a] text-sm'>
                            No items yet. Add your inventory items now!
                          </td>
                        </tr>
                      ) : (
                        items.map((row) => (
                          <tr
                            key={row.item_id}
                            className='group border-t border-[#e8d5d0]/60 hover:bg-[#ead8b6]/50'
                          >
                            <td className='py-3 px-4 text-[#4a4a4a] text-sm text-left w-[45%]'>
                              <span className='inline-flex items-center gap-2'>
                                <span>{row.name}</span>
                                <button
                                  type='button'
                                  onClick={() => openEditDialog(row)}
                                  className='opacity-0 group-hover:opacity-100 p-1 rounded text-black hover:bg-[#ead8b6]/70 transition-all cursor-pointer'
                                  aria-label='Edit ingredient'
                                >
                                  <FaRegEdit size={14} />
                                </button>
                              </span>
                            </td>
                            <td className='py-3 px-4 text-[#4a4a4a] text-sm text-center w-[25%]'>
                              {row.quantity}
                            </td>
                            <td className='py-3 px-4 text-[#4a4a4a] text-sm text-right w-[30%]'>
                              {row.unit}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
                <button
                  type='button'
                  onClick={openAddDialog}
                  className='absolute bottom-3 right-3 z-10 inline-flex items-center gap-2 px-4 py-1 rounded-full bg-[#F6C7B7] text-black font-medium text-sm hover:opacity-90 transition-opacity shadow-sm cursor-pointer'
                >
                  <FiPlus size={14} /> Add ingredient
                </button>
              </div>

              <div className='flex items-center gap-3 my-5'>
                <span className='flex-1 h-px bg-[#F2CEC2]' />
                <span className='text-[#F2CEC2] text-lg'>or</span>
                <span className='flex-1 h-px bg-[#F2CEC2]' />
              </div>

              <form
                onSubmit={handleQuickSubmit}
                className='flex gap-2 rounded-full bg-[#F6E7C8] px-2 pr-2 shadow-sm border border-[#e8d5d0]/60'
              >
                <input
                  type='text'
                  value={quickInput}
                  onChange={(e) => setQuickInput(e.target.value)}
                  disabled={quickSubmitting}
                  placeholder='Quick add (e.g. 2 eggs, 100g spinach)'
                  className='flex-1 px-4 py-2.5 bg-transparent text-[#4a4a4a] placeholder-[#4a4a4a]/60 focus:outline-none text-sm'
                />
                <button
                  type='submit'
                  disabled={quickSubmitting}
                  className='px-2.5 scale-70 -mr-2 rounded-full bg-[#e8c4c0]/80 text-black hover:bg-[#e8c4c0] transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed'
                  aria-label='Add ingredients'
                >
                  <IoArrowUp size={20} />
                </button>
              </form>
            </>
          )}
            </div>
          </div>
        </div>
      </main>

      {quickSubmitting && (
        <div
          className='fixed inset-0 z-[10056] flex items-center justify-center bg-black/55 backdrop-blur-[2px]'
          role='status'
          aria-live='polite'
          aria-label='Updating inventory'
        >
          <LoaderSpinner size='lg' color='#F2CEC2' />
        </div>
      )}

      <IngredientDialog
        open={dialogOpen}
        onClose={closeDialog}
        title={editingItem ? 'Edit ingredient' : 'Add ingredient'}
        submitLabel={editingItem ? 'Save' : 'Add'}
        initialValues={getDialogInitialValues()}
        onSubmit={handleDialogSubmit}
        onDelete={editingItem ? handleDeleteIngredient : undefined}
      />
    </div>
  )
}

export default Inventory
