"""Tests for the database module."""

import pytest
from pathlib import Path

from chatbot.core.database import DatabaseManager


@pytest.fixture
def db_manager():
    """Create a database manager for testing."""
    db_path = Path(__file__).parent.parent / "synthio.db"
    if not db_path.exists():
        pytest.skip("Database file not found")
    return DatabaseManager(str(db_path))


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_get_table_names(self, db_manager):
        """Test that we can retrieve table names."""
        tables = db_manager.get_table_names()
        assert len(tables) > 0
        assert "hcp_dim" in tables
        assert "fact_rx" in tables

    def test_get_table_schema(self, db_manager):
        """Test that we can retrieve table schema."""
        schema = db_manager.get_table_schema("hcp_dim")
        assert len(schema) > 0
        column_names = [col["name"] for col in schema]
        assert "hcp_id" in column_names
        assert "full_name" in column_names

    def test_execute_query_success(self, db_manager):
        """Test successful query execution."""
        df, error = db_manager.execute_query("SELECT * FROM hcp_dim LIMIT 5")
        assert error is None
        assert len(df) == 5

    def test_execute_query_error(self, db_manager):
        """Test query execution with invalid SQL."""
        df, error = db_manager.execute_query("SELECT * FROM nonexistent_table")
        assert error is not None
        assert len(df) == 0

    def test_get_sample_data(self, db_manager):
        """Test retrieving sample data."""
        df = db_manager.get_sample_data("hcp_dim", limit=3)
        assert len(df) == 3

    def test_get_row_count(self, db_manager):
        """Test getting row count."""
        count = db_manager.get_row_count("hcp_dim")
        assert count > 0

