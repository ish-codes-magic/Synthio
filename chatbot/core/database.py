"""Database connection and query execution utilities."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class DatabaseManager:
    """Manages database connections and query execution."""

    def __init__(self, db_path: str = "synthio.db"):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = Path(db_path)
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        """Get or create the SQLAlchemy engine."""
        if self._engine is None:
            self._engine = create_engine(f"sqlite:///{self.db_path}")
        return self._engine

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str) -> tuple[pd.DataFrame, str | None]:
        """
        Execute a SQL query and return results as a DataFrame.

        Args:
            query: SQL query string to execute

        Returns:
            Tuple of (DataFrame with results, error message or None)
        """
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(text(query), conn)
                return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def get_table_names(self) -> list[str]:
        """Get all table names in the database."""
        with self.get_connection() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            return [row[0] for row in result]

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """
        Get the schema for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            List of column information dictionaries
        """
        with self.get_connection() as conn:
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = []
            for row in result:
                columns.append({
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": row[3],
                    "default_value": row[4],
                    "pk": row[5],
                })
            return columns

    def get_sample_data(self, table_name: str, limit: int = 3) -> pd.DataFrame:
        """
        Get sample data from a table.

        Args:
            table_name: Name of the table
            limit: Number of sample rows to retrieve

        Returns:
            DataFrame with sample data
        """
        df, _ = self.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")
        return df

    def get_row_count(self, table_name: str) -> int:
        """Get the number of rows in a table."""
        with self.get_connection() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar() or 0
