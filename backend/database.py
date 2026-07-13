import sqlite3
import pandas as pd
import os

DB_PATH = "enterprise.db"

def init_db_from_csv(csv_path):
    """Reads the expanded enterprise CSV dataset and builds a normalized relational DB."""
    if not os.path.exists(csv_path):
        print(f"Error: Source dataset not found at {csv_path}")
        return

    # Load unified data sheet
    df = pd.read_csv(csv_path)

    # 1. Isolate and normalize unique customer records
    users_df = df[['user_id', 'customer_name', 'email']].drop_duplicates().reset_index(drop=True)

    # 2. Isolate unique transaction records
    orders_df = df[['order_id', 'user_id', 'product_name', 'category', 'total_amount', 'status']].drop_duplicates().reset_index(drop=True)

    # Initialize connection to local SQLite database instance
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing definitions to prevent duplicate schema append mutations
    cursor.execute("DROP TABLE IF EXISTS orders;")
    cursor.execute("DROP TABLE IF EXISTS users;")

    # Build relational table schemas
    cursor.execute("""
    CREATE TABLE users (
        user_id INTEGER PRIMARY KEY,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE
    );
    """)

    cursor.execute("""
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    );
    """)

    conn.commit()

    # Populate tables using Pandas internal SQL integration layers
    users_df.to_sql('users', conn, if_exists='append', index=False)
    orders_df.to_sql('orders', conn, if_exists='append', index=False)

    print(f"📊 [Success] Database 'enterprise.db' initialized and seeded. {len(users_df)} users and {len(orders_df)} orders created.")
    conn.close()

def execute_query(sql_query):
    """Executes safe SQL commands directly against the database cluster."""
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(sql_query, conn)
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

# --- ADD THIS FUNCTION TO FIX THE IMPORT ERROR ---
def get_db_schema():
    """Returns the text representation of the database schema for Ollama context grounding."""
    schema_info = """
Table: users
Columns:
  - user_id (INTEGER, PRIMARY KEY)
  - customer_name (TEXT)
  - email (TEXT)

Table: orders
Columns:
  - order_id (INTEGER, PRIMARY KEY)
  - user_id (INTEGER, FOREIGN KEY references users.user_id)
  - product_name (TEXT)
  - category (TEXT)
  - total_amount (REAL)
  - status (TEXT)
    """
    return schema_info.strip()

if __name__ == "__main__":
    # Fallback default script check
    init_db_from_csv(os.path.join("..", "data", "business_data.csv"))