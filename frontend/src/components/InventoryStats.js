import React from "react";
import "./InventoryStats.css";

const InventoryStats = ({ stats }) => {
  return (
    <div className="inventory-stats">
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total_items}</div>
          <div className="stat-label">Total Items</div>
        </div>

        <div className="stat-card">
          <div className="stat-value">
            {Object.keys(stats.categories || {}).length}
          </div>
          <div className="stat-label">Categories</div>
        </div>

        {stats.categories && Object.entries(stats.categories).length > 0 && (
          <div className="stat-card categories-card">
            <div className="stat-label">Items by Category</div>
            <div className="categories-list">
              {Object.entries(stats.categories).map(([category, count]) => (
                <div key={category} className="category-stat">
                  <span className="category-name">{category}</span>
                  <span className="category-count">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InventoryStats;
