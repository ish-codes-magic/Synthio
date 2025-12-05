"""Tests for the schema module."""

import pytest
from pathlib import Path

from chatbot.core.database import DatabaseManager
from chatbot.core.schema import get_database_schema, get_table_relationships


@pytest.fixture
def db_manager():
    """Create a database manager for testing."""
    db_path = Path(__file__).parent.parent / "synthio.db"
    if not db_path.exists():
        pytest.skip("Database file not found")
    return DatabaseManager(str(db_path))


class TestSchemaGeneration:
    """Tests for schema generation functions."""

    def test_get_database_schema(self, db_manager):
        """Test that schema context is generated correctly."""
        schema = get_database_schema(db_manager, include_samples=True)
        assert len(schema) > 0
        assert "hcp_dim" in schema
        assert "fact_rx" in schema
        assert "Healthcare Professionals" in schema

    def test_get_database_schema_without_samples(self, db_manager):
        """Test schema generation without sample data."""
        schema = get_database_schema(db_manager, include_samples=False)
        assert len(schema) > 0
        assert "hcp_dim" in schema

    def test_get_table_relationships(self):
        """Test table relationships mapping."""
        relationships = get_table_relationships()
        assert "hcp_dim" in relationships
        assert "territory_dim" in relationships["hcp_dim"]
        assert "fact_rx" in relationships
        assert "hcp_dim" in relationships["fact_rx"]

