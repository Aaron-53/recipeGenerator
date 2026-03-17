"""
Simple test runner for Inventory functionality
Run with: python test_inventory.py
"""

import sys

from datetime import datetime

# Mock test data
test_passed = 0
test_failed = 0


def test_inventory_schema_validation():
    """Test inventory schema validation"""
    from schemas.inventory import InventoryItemCreate

    # Valid item
    try:
        item = InventoryItemCreate(
            name="Tomatoes",
            quantity=5.0,
            unit="kg",
            category="vegetables",
            notes="Fresh organic tomatoes",
        )
        assert item.name == "Tomatoes"
        assert item.quantity == 5.0
        print("✓ Inventory schema validation - valid item")
        return True
    except Exception as e:
        print(f"✗ Inventory schema validation - valid item: {e}")
        return False


def test_inventory_item_response():
    """Test inventory item response schema"""
    from schemas.inventory import InventoryItemResponse

    try:
        response = InventoryItemResponse(
            item_id="123456",
            user_id="user123",
            name="Milk",
            quantity=2.0,
            unit="liters",
            category="dairy",
            notes=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert response.name == "Milk"
        assert response.quantity == 2.0
        print("✓ Inventory item response schema")
        return True
    except Exception as e:
        print(f"✗ Inventory item response schema: {e}")
        return False


def test_inventory_update_partial():
    """Test inventory update with partial data"""
    from schemas.inventory import InventoryItemUpdate

    try:
        # Update only quantity
        update = InventoryItemUpdate(quantity=10.5)
        assert update.quantity == 10.5
        assert update.name is None

        # Update only name
        update2 = InventoryItemUpdate(name="Updated Item")
        assert update2.name == "Updated Item"
        assert update2.quantity is None

        print("✓ Inventory partial update schema")
        return True
    except Exception as e:
        print(f"✗ Inventory partial update schema: {e}")
        return False


def test_inventory_quantity_validation():
    """Test inventory quantity must be positive"""
    from schemas.inventory import InventoryItemCreate
    from pydantic import ValidationError

    try:
        # Negative quantity should fail
        try:
            item = InventoryItemCreate(
                name="Test", quantity=-5.0, unit="kg", category="test"
            )
            print("✗ Inventory quantity validation - allowed negative")
            return False
        except ValidationError:
            pass

        # Zero quantity should fail
        try:
            item = InventoryItemCreate(
                name="Test", quantity=0, unit="kg", category="test"
            )
            print("✗ Inventory quantity validation - allowed zero")
            return False
        except ValidationError:
            pass

        print("✓ Inventory quantity validation")
        return True
    except Exception as e:
        print(f"✗ Inventory quantity validation: {e}")
        return False


def test_inventory_required_fields():
    """Test inventory required fields"""
    from schemas.inventory import InventoryItemCreate
    from pydantic import ValidationError

    try:
        # Missing name should fail
        try:
            item = InventoryItemCreate(quantity=5.0, unit="kg")
            print("✗ Inventory required fields - missing name allowed")
            return False
        except (ValidationError, TypeError):
            pass

        # Missing quantity should fail
        try:
            item = InventoryItemCreate(name="Test", unit="kg")
            print("✗ Inventory required fields - missing quantity allowed")
            return False
        except (ValidationError, TypeError):
            pass

        # Missing unit should fail
        try:
            item = InventoryItemCreate(name="Test", quantity=5.0)
            print("✗ Inventory required fields - missing unit allowed")
            return False
        except (ValidationError, TypeError):
            pass

        print("✓ Inventory required fields validation")
        return True
    except Exception as e:
        print(f"✗ Inventory required fields validation: {e}")
        return False


def test_inventory_categories():
    """Test inventory with different categories"""
    from schemas.inventory import InventoryItemCreate

    try:
        categories = ["vegetables", "fruits", "dairy", "meat", "grains"]

        for category in categories:
            item = InventoryItemCreate(
                name=f"Test {category}",
                quantity=1.0,
                unit="unit",
                category=category,
            )
            assert item.category == category

        print("✓ Inventory categories")
        return True
    except Exception as e:
        print(f"✗ Inventory categories: {e}")
        return False


def test_inventory_optional_fields():
    """Test inventory with optional fields"""
    from schemas.inventory import InventoryItemCreate

    try:
        # Without optional fields
        item1 = InventoryItemCreate(name="Basic Item", quantity=1.0, unit="piece")
        assert item1.category is None
        assert item1.notes is None

        # With optional fields
        item2 = InventoryItemCreate(
            name="Full Item",
            quantity=2.0,
            unit="kg",
            category="test",
            notes="Some notes",
        )
        assert item2.category == "test"
        assert item2.notes == "Some notes"

        print("✓ Inventory optional fields")
        return True
    except Exception as e:
        print(f"✗ Inventory optional fields: {e}")
        return False


# Run all tests
print("=" * 60)
print("Running Inventory Tests")
print("=" * 60)

tests = [
    test_inventory_schema_validation,
    test_inventory_item_response,
    test_inventory_update_partial,
    test_inventory_quantity_validation,
    test_inventory_required_fields,
    test_inventory_categories,
    test_inventory_optional_fields,
]

passed = 0
failed = 0

for test in tests:
    try:
        if test():
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"✗ {test.__name__}: {e}")
        failed += 1

print("=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
