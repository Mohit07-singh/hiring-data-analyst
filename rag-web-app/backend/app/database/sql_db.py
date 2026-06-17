import sqlite3
import pandas as pd
import sys
from pathlib import Path

# Set up sys.path for importing app modules when running directly
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

# Cache the connection globally to prevent reloading CSV multiple times
_sql_conn = None

def get_sql_conn() -> sqlite3.Connection:
    """
    Initializes and returns an in-memory SQLite database connection.
    Loads the candidate dataset from the CSV file on the first call.
    """
    global _sql_conn
    if _sql_conn is not None:
        return _sql_conn
        
    current_file = Path(__file__).resolve()
    # Resolve workspace root (four levels up from: rag-web-app/backend/app/database/sql_db.py)
    workspace_root = current_file.parent.parent.parent.parent
    csv_path = workspace_root / "data" / "raw" / "fresher_hiring_india_dataset.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Candidate CSV dataset not found at: {csv_path}")
        
    print(f"Loading candidate dataset from CSV into SQLite: {csv_path}...")
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Normalize column names for standard SQL (lower case, strip spaces, replace spaces/hyphens with underscores)
    df.columns = [c.strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    
    # Connect to in-memory SQLite DB
    _sql_conn = sqlite3.connect(":memory:", check_same_thread=False)
    
    # Load into candidates table
    df.to_sql("candidates", _sql_conn, if_exists="replace", index=False)
    
    print("In-memory SQLite database initialized with 'candidates' table.")
    return _sql_conn

def run_sql_query(query: str):
    """
    Executes a SQL query on the candidates database.
    Returns:
        tuple: (list of dicts representing rows, error_message string or None)
    """
    try:
        conn = get_sql_conn()
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Check if the query is a SELECT statement returning results
        if cursor.description is not None:
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results, None
        else:
            conn.commit()
            return [{"message": "Query executed successfully. Row count changed: " + str(cursor.rowcount)}], None
            
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    # Local quick test run
    print("\n--- Running sql_db.py Local Test ---")
    try:
        conn = get_sql_conn()
        res, err = run_sql_query("SELECT COUNT(*) as total FROM candidates")
        print("Test Query Result:", res)
        print("Test Query Error:", err)
    except Exception as e:
        print("Error during local test:", e)
