import os
import sys
import argparse
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

def check_schema(database_url=None):
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("[ERROR] DATABASE_URL environment variable is missing.")
        sys.exit(1)
        
    print(f"Connecting to database...")
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
    except SQLAlchemyError as e:
        print(f"[ERROR] Failed to connect or inspect database: {e}")
        sys.exit(1)

    required_tables_and_columns = {
        "user": [
            "id", "name", "email", "password_hash", "phone", "role",
            "admin_role", "is_admin", "is_active", "created_at"
        ],
        "translator_profile": ["id", "user_id", "title", "bio", "languages", "badges", "rating", "total_reviews", "total_jobs", "response_time", "is_verified"],
        "translator_preference": ["id", "translator_id", "languages", "language_pairs", "service_types", "notify_new_jobs", "notify_messages", "notify_contracts", "notify_reviews", "created_at", "updated_at"],
        "hirer_profile": ["id", "user_id", "title", "company", "location", "rating"],
        "service": ["id", "profile_id", "name", "description", "languages", "category", "basic_price", "standard_price", "premium_price", "basic_delivery", "standard_delivery", "premium_delivery"],
        "job": ["id", "hirer_id", "title", "description", "category", "category_group", "service_type", "source_lang", "target_lang", "budget_type", "budget_min", "budget_max", "event_date", "event_time_start", "event_time_end", "event_location", "deadline", "status", "is_flagged", "created_at"],
        "proposal": ["id", "job_id", "translator_id", "cover_letter", "price", "time_estimate", "status", "created_at"],
        "contract": ["id", "job_id", "service_id", "proposal_id", "hirer_id", "translator_id", "agreed_price", "scheduled_date", "scheduled_time_start", "scheduled_time_end", "location", "status", "created_at", "updated_at"],
        "message": ["id", "contract_id", "sender_id", "content", "is_read", "created_at"],
        "direct_message": ["id", "sender_id", "receiver_id", "content", "is_read", "created_at"],
        "deliverable": ["id", "contract_id", "filename", "filepath", "created_at"],
        "review": ["id", "contract_id", "reviewer_id", "reviewee_id", "rating", "comment", "is_hidden", "created_at"],
        "notification": ["id", "user_id", "type", "title", "message", "url", "is_read", "related_job_id", "related_contract_id", "related_review_id", "related_proposal_id", "created_at"],
        "translator_schedule": ["id", "translator_id", "contract_id", "job_id", "service_id", "scheduled_date", "start_time", "end_time", "buffer_before_minutes", "buffer_after_minutes", "status", "created_at", "expires_at"],
        "report": ["id", "reporter_id", "target_type", "target_id", "reason", "description", "evidence_url", "status", "related_job_id", "related_contract_id", "created_at", "updated_at"],
        "payment_transaction": ["id", "contract_id", "user_id", "amount", "status", "payment_method", "transaction_ref", "created_at", "updated_at"],
        "admin_notification": ["id", "type", "title", "message", "url", "is_read", "related_id", "created_at"],
        "login_attempt": ["id", "email", "ip_address", "success", "created_at"],
        "admin_audit_log": ["id", "admin_id", "action", "target_type", "target_id", "description", "ip_address", "user_agent", "extra_data", "created_at"],
        # TASK 1: added job_schedule
        "job_schedule": ["id", "job_id", "scheduled_date", "start_time", "end_time", "created_at", "updated_at"],
    }
    
    existing_tables = inspector.get_table_names()
    print("\n--- Schema Check ---")
    
    missing_tables = []
    missing_columns = {}
    
    for table, columns in required_tables_and_columns.items():
        if table not in existing_tables:
            missing_tables.append(table)
            print(f"❌ Table: {table} (MISSING)")
            continue
            
        print(f"✅ Table: {table}")
        existing_columns = [col['name'] for col in inspector.get_columns(table)]
        
        missing_cols_in_table = []
        for col in columns:
            if col not in existing_columns:
                missing_cols_in_table.append(col)
                print(f"  ❌ Column: {col} (MISSING)")
            else:
                pass # print(f"  ✅ Column: {col}")
        
        if missing_cols_in_table:
            missing_columns[table] = missing_cols_in_table
    
    # Check exclusion constraint in translator_schedule
    print("\n--- Constraints Check ---")
    if "translator_schedule" in existing_tables:
        with engine.connect() as conn:
            query = text("""
                SELECT conname 
                FROM pg_constraint 
                WHERE conrelid = 'translator_schedule'::regclass AND contype = 'x';
            """)
            try:
                result = conn.execute(query).fetchall()
                constraints = [row[0] for row in result]
                if "no_overlapping_schedules" in constraints:
                    print("✅ Exclusion Constraint: no_overlapping_schedules")
                else:
                    print("❌ Exclusion Constraint: no_overlapping_schedules (MISSING)")
            except Exception as e:
                print(f"⚠️ Could not verify exclusion constraints (might be SQLite or syntax error): {e}")
                
    print("\n--- Summary ---")
    if not missing_tables and not missing_columns:
        print("✅ Schema is fully in sync with models.py")
        sys.exit(0)
    else:
        print("⚠️ Schema drift detected.")
        if missing_tables:
            print(f"Missing tables: {', '.join(missing_tables)}")
        if missing_columns:
            for t, cols in missing_columns.items():
                print(f"Table '{t}' missing columns: {', '.join(cols)}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", help="Database URL")
    args = parser.parse_args()
    check_schema(args.db)
