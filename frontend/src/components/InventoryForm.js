import React, { useState, useEffect } from "react";
import "./InventoryForm.css";

const InventoryForm = ({ item, onSubmit, onCancel }) => {
  const [formData, setFormData] = useState({
    name: "",
    quantity: "",
    unit: "",
    category: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (item) {
      setFormData({
        name: item.name || "",
        quantity: item.quantity || "",
        unit: item.unit || "",
        category: item.category || "",
        notes: item.notes || "",
      });
    }
  }, [item]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Convert quantity to number
      const submitData = {
        ...formData,
        quantity: parseFloat(formData.quantity),
      };

      // Remove empty optional fields
      if (!submitData.category) delete submitData.category;
      if (!submitData.notes) delete submitData.notes;

      await onSubmit(submitData);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="inventory-form">
      <h2>{item ? "Edit Item" : "Add New Item"}</h2>

      {error && <div className="error-message">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="name" className="form-label">
            Item Name *
          </label>
          <input
            type="text"
            id="name"
            name="name"
            className="form-control"
            value={formData.name}
            onChange={handleChange}
            required
            maxLength={100}
            disabled={loading}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="quantity" className="form-label">
              Quantity *
            </label>
            <input
              type="number"
              id="quantity"
              name="quantity"
              className="form-control"
              value={formData.quantity}
              onChange={handleChange}
              required
              min="0.01"
              step="0.01"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="unit" className="form-label">
              Unit *
            </label>
            <input
              type="text"
              id="unit"
              name="unit"
              className="form-control"
              value={formData.unit}
              onChange={handleChange}
              required
              maxLength={20}
              placeholder="e.g., kg, lbs, pieces"
              disabled={loading}
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="category" className="form-label">
            Category
          </label>
          <input
            type="text"
            id="category"
            name="category"
            className="form-control"
            value={formData.category}
            onChange={handleChange}
            maxLength={50}
            placeholder="e.g., vegetables, meat, dairy"
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label htmlFor="notes" className="form-label">
            Notes
          </label>
          <textarea
            id="notes"
            name="notes"
            className="form-control"
            value={formData.notes}
            onChange={handleChange}
            maxLength={500}
            rows={4}
            placeholder="Additional information..."
            disabled={loading}
          />
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={onCancel}
            className="btn btn-secondary"
            disabled={loading}
          >
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Saving..." : item ? "Update Item" : "Add Item"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default InventoryForm;
