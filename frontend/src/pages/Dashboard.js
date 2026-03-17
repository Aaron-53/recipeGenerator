import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { inventoryAPI } from "../services/api";
import InventoryList from "../components/InventoryList";
import InventoryForm from "../components/InventoryForm";
import InventoryStats from "../components/InventoryStats";
import "./Dashboard.css";

const Dashboard = () => {
  const { user, logout } = useAuth();
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [filterCategory, setFilterCategory] = useState("");

  useEffect(() => {
    loadData();
  }, [filterCategory]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");

      const [itemsResponse, statsResponse] = await Promise.all([
        inventoryAPI.getAllItems(filterCategory || null),
        inventoryAPI.getStats(),
      ]);

      setItems(itemsResponse.data);
      setStats(statsResponse.data);
    } catch (err) {
      console.error("Error loading data:", err);
      setError(err.response?.data?.detail || "Failed to load inventory data");
    } finally {
      setLoading(false);
    }
  };

  const handleAddItem = () => {
    setEditingItem(null);
    setShowForm(true);
  };

  const handleEditItem = (item) => {
    setEditingItem(item);
    setShowForm(true);
  };

  const handleDeleteItem = async (itemId) => {
    if (!window.confirm("Are you sure you want to delete this item?")) {
      return;
    }

    try {
      await inventoryAPI.deleteItem(itemId);
      await loadData();
    } catch (err) {
      console.error("Error deleting item:", err);
      alert(err.response?.data?.detail || "Failed to delete item");
    }
  };

  const handleFormSubmit = async (formData) => {
    try {
      if (editingItem) {
        await inventoryAPI.updateItem(editingItem.item_id, formData);
      } else {
        await inventoryAPI.createItem(formData);
      }

      setShowForm(false);
      setEditingItem(null);
      await loadData();
    } catch (err) {
      console.error("Error saving item:", err);
      throw new Error(err.response?.data?.detail || "Failed to save item");
    }
  };

  const handleFormCancel = () => {
    setShowForm(false);
    setEditingItem(null);
  };

  const handleLogout = async () => {
    await logout();
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="container">
          <div className="header-content">
            <h1>Inventory Management</h1>
            <div className="header-actions">
              <span className="user-welcome">Welcome, {user?.username}!</span>
              <button onClick={handleLogout} className="btn btn-secondary">
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="container">
          {error && <div className="error-message">{error}</div>}

          {stats && <InventoryStats stats={stats} />}

          <div className="inventory-section">
            <div className="section-header">
              <h2>Your Inventory</h2>
              <div className="section-actions">
                <select
                  className="form-control category-filter"
                  value={filterCategory}
                  onChange={(e) => setFilterCategory(e.target.value)}
                >
                  <option value="">All Categories</option>
                  {stats?.categories &&
                    Object.keys(stats.categories).map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                </select>
                <button onClick={handleAddItem} className="btn btn-primary">
                  Add Item
                </button>
              </div>
            </div>

            {showForm && (
              <div className="form-modal">
                <div className="form-modal-content">
                  <InventoryForm
                    item={editingItem}
                    onSubmit={handleFormSubmit}
                    onCancel={handleFormCancel}
                  />
                </div>
              </div>
            )}

            <InventoryList
              items={items}
              onEdit={handleEditItem}
              onDelete={handleDeleteItem}
            />
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
