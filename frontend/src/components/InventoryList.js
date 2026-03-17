import React from "react";
import "./InventoryList.css";

const InventoryList = ({ items, onEdit, onDelete }) => {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <h3>No items in inventory</h3>
        <p>Add your first item to get started!</p>
      </div>
    );
  }

  return (
    <div className="inventory-list">
      <div className="inventory-grid">
        {items.map((item) => (
          <div key={item.item_id} className="inventory-item-card">
            <div className="item-header">
              <h3 className="item-name">{item.name}</h3>
              {item.category && (
                <span className="item-category">{item.category}</span>
              )}
            </div>

            <div className="item-details">
              <div className="item-quantity">
                <strong>{item.quantity}</strong> {item.unit}
              </div>

              {item.notes && <p className="item-notes">{item.notes}</p>}
            </div>

            <div className="item-meta">
              <small>
                Updated: {new Date(item.updated_at).toLocaleDateString()}
              </small>
            </div>

            <div className="item-actions">
              <button
                onClick={() => onEdit(item)}
                className="btn btn-secondary btn-sm"
              >
                Edit
              </button>
              <button
                onClick={() => onDelete(item.item_id)}
                className="btn btn-danger btn-sm"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InventoryList;
