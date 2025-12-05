"""
Script to convert all CSV files in the data folder to SQL tables.

Usage:
    python csv_to_sql.py                    # Uses SQLite (default)
    python csv_to_sql.py --db postgresql    # Uses PostgreSQL
    python csv_to_sql.py --db mysql         # Uses MySQL
"""

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


def get_database_url(db_type: str = "sqlite") -> str:
    """Get the database connection URL based on database type."""
    
    if db_type == "sqlite":
        # SQLite - file-based, no server needed
        return "sqlite:///synthio.db"
    
    elif db_type == "postgresql":
        # PostgreSQL - requires server running
        # Default connection: postgresql://user:password@localhost:5432/database
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        database = os.getenv("POSTGRES_DB", "synthio")
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    elif db_type == "mysql":
        # MySQL - requires server running
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        user = os.getenv("MYSQL_USER", "root")
        password = os.getenv("MYSQL_PASSWORD", "password")
        database = os.getenv("MYSQL_DB", "synthio")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def csv_to_sql_tables(data_folder: str = "data", db_type: str = "sqlite") -> None:
    """
    Convert all CSV files in the data folder to SQL tables.
    
    Args:
        data_folder: Path to the folder containing CSV files
        db_type: Type of database ('sqlite', 'postgresql', 'mysql')
    """
    data_path = Path(data_folder)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data folder not found: {data_folder}")
    
    # Get all CSV files
    csv_files = list(data_path.glob("*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {data_folder}")
        return
    
    print(f"Found {len(csv_files)} CSV files to process")
    
    # Create database connection
    db_url = get_database_url(db_type)
    engine = create_engine(db_url)
    
    print(f"Connecting to database: {db_type}")
    
    # Process each CSV file
    for csv_file in csv_files:
        table_name = csv_file.stem  # Filename without extension
        
        print(f"\nProcessing: {csv_file.name} -> {table_name}")
        
        # Read CSV file
        df = pd.read_csv(csv_file)
        
        print(f"  Rows: {len(df)}, Columns: {list(df.columns)}")
        
        # Write to SQL table (replace if exists)
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="replace",
            index=False
        )
        
        print(f"  ✓ Created table '{table_name}'")
    
    # Verify tables were created
    print("\n" + "=" * 50)
    print("Database Summary")
    print("=" * 50)
    
    with engine.connect() as conn:
        if db_type == "sqlite":
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ))
        elif db_type == "postgresql":
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'"
            ))
        elif db_type == "mysql":
            result = conn.execute(text("SHOW TABLES"))
        
        tables = [row[0] for row in result]
        
        print(f"\nCreated {len(tables)} tables:")
        for table in tables:
            # Get row count
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.scalar()
            print(f"  • {table}: {count} rows")
    
    print(f"\nDatabase file: {db_url}")
    print("Done!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convert CSV files to SQL database tables"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="sqlite",
        choices=["sqlite", "postgresql", "mysql"],
        help="Database type (default: sqlite)"
    )
    parser.add_argument(
        "--data-folder",
        type=str,
        default="data",
        help="Folder containing CSV files (default: data)"
    )
    
    args = parser.parse_args()
    
    csv_to_sql_tables(data_folder=args.data_folder, db_type=args.db)


if __name__ == "__main__":
    main()

