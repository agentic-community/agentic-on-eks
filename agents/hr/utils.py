import os
import sqlite3
import logging
import datetime
import yaml
import random
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        # Return a default configuration
        return {
            "model_information": {
                "crewAI_model_info": {
                    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "inference_parameters": {
                        "temperature": 0.7,
                        "max_tokens": 4096,
                        "top_p": 0.9
                    }
                }
            }
        }

def get_db_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database"""
    db_path = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(__file__), 'hr_database.sqlite'))
    logger.info(f"Using database at: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def close_db_connection(conn: sqlite3.Connection) -> None:
    """Close the database connection"""
    if conn:
        conn.close()

def init_db() -> None:
    """Initialize the database with required tables"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create employees table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL
        )
        ''')
        
        # Create leave_policies table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_policies (
            policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_name TEXT NOT NULL,
            annual_days INTEGER NOT NULL,
            max_carryover_days INTEGER NOT NULL,
            probation_period_days INTEGER NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT NOT NULL
        )
        ''')
        
        # Create employee_policies table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            policy_id INTEGER NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id),
            FOREIGN KEY (policy_id) REFERENCES leave_policies (policy_id)
        )
        ''')
        
        # Create leave_balances table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            accrued_days REAL NOT NULL,
            used_days REAL NOT NULL,
            carryover REAL NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
        )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        close_db_connection(conn)

def insert_sample_data(conn: sqlite3.Connection, num_employees: int = 30) -> None:
    """Insert sample data into the database"""
    try:
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM employees")
        employee_count = cursor.fetchone()[0]
        
        if employee_count > 0:
            logger.info("Sample data already exists, skipping insertion")
            return
        
        # Insert leave policies
        policies = [
            ("Standard", 20, 5, 90, "2020-01-01", "2099-12-31"),
            ("Executive", 30, 10, 30, "2020-01-01", "2099-12-31"),
            ("New Hire", 15, 3, 180, "2020-01-01", "2099-12-31")
        ]
        
        cursor.executemany(
            "INSERT INTO leave_policies (policy_name, annual_days, max_carryover_days, probation_period_days, effective_from, effective_to) VALUES (?, ?, ?, ?, ?, ?)",
            policies
        )
        
        # Get policy IDs
        cursor.execute("SELECT policy_id, policy_name FROM leave_policies")
        policy_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        # Insert employees and their policies
        current_year = datetime.datetime.now().year
        
        for i in range(1, num_employees + 1):
            # Generate employee data
            employee_id = f"EMP{i:04d}"
            name = f"Employee {i}"
            
            # Random start date in the last 5 years
            years_ago = random.randint(0, 5)
            start_date = datetime.date(current_year - years_ago, 
                                      random.randint(1, 12), 
                                      random.randint(1, 28))
            
            # Insert employee
            cursor.execute(
                "INSERT INTO employees (employee_id, name, start_date) VALUES (?, ?, ?)",
                (employee_id, name, start_date.isoformat())
            )
            
            # Assign policy based on employee number
            if i <= 5:  # First 5 employees get Executive policy
                policy_id = policy_map["Executive"]
            elif i <= 10:  # Next 5 get New Hire policy
                policy_id = policy_map["New Hire"]
            else:  # Rest get Standard policy
                policy_id = policy_map["Standard"]
            
            # Insert employee policy
            cursor.execute(
                "INSERT INTO employee_policies (employee_id, policy_id, effective_from, effective_to) VALUES (?, ?, ?, ?)",
                (employee_id, policy_id, start_date.isoformat(), "2099-12-31")
            )
            
            # Insert leave balance for current year
            policy_name = next(name for name, id in policy_map.items() if id == policy_id)
            annual_days = 30 if policy_name == "Executive" else 20 if policy_name == "Standard" else 15
            
            # Calculate accrued days based on how far we are in the current year
            today = datetime.date.today()
            days_in_year = 366 if current_year % 4 == 0 else 365
            days_elapsed = (today - datetime.date(current_year, 1, 1)).days
            accrued_proportion = days_elapsed / days_in_year
            accrued_days = round(annual_days * accrued_proportion, 1)
            
            # Random used days (less than accrued)
            used_days = round(random.uniform(0, accrued_days * 0.8), 1)
            
            # Random carryover (0-5 days)
            carryover = round(random.uniform(0, 5), 1)
            
            cursor.execute(
                "INSERT INTO leave_balances (employee_id, year, accrued_days, used_days, carryover) VALUES (?, ?, ?, ?, ?)",
                (employee_id, current_year, accrued_days, used_days, carryover)
            )
        
        conn.commit()
        logger.info(f"Inserted {num_employees} sample employees with policies and leave balances")
    
    except Exception as e:
        logger.error(f"Error inserting sample data: {e}")
        conn.rollback()
        raise
