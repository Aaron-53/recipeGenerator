import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import signupImage from '../assets/signup_bg.svg'
import { FiPlus } from 'react-icons/fi'
import { FaRegEdit } from 'react-icons/fa'
import { IoArrowUp } from 'react-icons/io5'
import { FiLogOut } from 'react-icons/fi'
import IngredientDialog from '../components/IngredientDialog'
import { useAuth } from '../context/AuthContext'
import { inventoryAPI } from '../services/api'

const Inventory = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [quickInput, setQuickInput] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState(null)

  const loadItems = async () => {
    try {
      setError('')
      const res = await inventoryAPI.getAllItems()
      setItems(res.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load inventory')
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadItems()
  }, [])

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
      const msg = err.response?.data?.detail || 'Failed to save'
      setError(msg)
    }
  }

  const handleDeleteIngredient = async () => {
    if (!editingItem) return
    if (!window.confirm('Delete this item?')) return
    try {
      await inventoryAPI.deleteItem(editingItem.item_id)
      closeDialog()
      await loadItems()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete')
    }
  }

  const handleLogout = async () => {
    await logout()
    navigate('/', { replace: true })
  }

  const handleQuickSubmit = (e) => {
    e?.preventDefault()
    setQuickInput('')
  }

  return (
    <div className='fixed inset-0 overflow-x-hidden'>
      <img
        src={signupImage}
        alt=""
        className='h-full w-full min-h-full min-w-full object-cover object-center'
        aria-hidden
      />
      <div className='absolute inset-0 z-10 flex items-center justify-end'>
        <div className='w-full max-w-[650px] px-6 md:px-14 lg:px-16 lg:mr-8'>
          <div className='flex items-center justify-between mb-6'>
            <h1 className='text-[#F2CEC2] text-xl md:text-3xl font-medium'>
              What&apos;s in your kitchen?
            </h1>
            <button
              type='button'
              onClick={handleLogout}
              className='inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F6C7B7]/90 text-[#5C6E43] font-medium text-sm hover:opacity-90 cursor-pointer'
              aria-label='Log out'
            >
              <FiLogOut size={16} /> Logout
            </button>
          </div>

          {error && (
            <p className='mb-4 text-red-200 text-sm bg-red-900/40 px-4 py-2 rounded-lg'>
              {error}
            </p>
          )}

          {loading ? (
            <p className='text-[#F2CEC2]'>Loading inventory...</p>
          ) : (
            <>
              <div className='relative rounded-xl bg-[#F6E7C8] overflow-hidden shadow-sm flex flex-col h-[320px]'>
                <table className='w-full border-collapse table-fixed shrink-0'>
                  <thead>
                    <tr className='bg-[#F6C7B7]'>
                      <th className='text-left text-[#5C6E43] font-semibold py-3 px-4 text-lg w-[45%]'>
                        Ingredient
                      </th>
                      <th className='text-center text-[#5C6E43] font-semibold py-3 px-4 text-lg w-[25%]'>
                        Quantity
                      </th>
                      <th className='text-right text-[#5C6E43] font-semibold py-3 px-4 text-lg w-[30%]'>
                        Unit
                      </th>
                    </tr>
                  </thead>
                </table>
                <div className='inventory-rows-scroll overflow-auto min-h-0 flex-1'>
                  <table className='w-full border-collapse table-fixed'>
                    <tbody>
                      {items.length === 0 ? (
                        <tr>
                          <td colSpan={3} className='py-8 px-4 text-center text-[#4a4a4a] text-sm'>
                            No items yet. Add your first ingredient below.
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
                  placeholder='Quick add (e.g. 2 eggs, 100g spinach)'
                  className='flex-1 px-4 py-2.5 bg-transparent text-[#4a4a4a] placeholder-[#4a4a4a]/60 focus:outline-none text-sm'
                />
                <button
                  type='submit'
                  className='px-2.5 scale-70 -mr-2 rounded-full bg-[#e8c4c0]/80 text-black hover:bg-[#e8c4c0] transition-colors cursor-pointer'
                  aria-label='Add ingredients'
                >
                  <IoArrowUp size={20} />
                </button>
              </form>
            </>
          )}
        </div>
      </div>

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
