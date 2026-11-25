import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import app
from models import db
from sqlalchemy import text

def create_performance_indexes():
    indexes = [
        # TranslatorProfile
        ("idx_translator_profile_user_id", "translator_profile", ["user_id"]),
        ("idx_translator_profile_rating", "translator_profile", ["rating"]),
        ("idx_translator_profile_is_public", "translator_profile", ["is_public"]),
        ("idx_translator_profile_is_verified", "translator_profile", ["is_verified"]),
        
        # Proposal
        ("idx_proposal_translator_id", "proposal", ["translator_id"]),
        ("idx_proposal_job_id", "proposal", ["job_id"]),
        ("idx_proposal_status", "proposal", ["status"]),
        
        # Job
        ("idx_job_hirer_id", "job", ["hirer_id"]),
        ("idx_job_closed_at", "job", ["closed_at"]),
        
        # Contract
        ("idx_contract_hirer_id", "contract", ["hirer_id"]),
        ("idx_contract_translator_id", "contract", ["translator_id"]),
        
        # Review
        ("idx_review_reviewee_id", "review", ["reviewee_id"]),
        ("idx_review_is_hidden", "review", ["is_hidden"]),
        
        # InterpreterService
        ("idx_interpreter_service_user_id", "interpreter_service", ["user_id"]),
        ("idx_interpreter_service_is_active", "interpreter_service", ["is_active"]),
        
        # Service
        ("idx_service_profile_id", "service", ["profile_id"]),
    ]

    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()
        created = 0
        try:
            for idx_name, table, cols in indexes:
                cols_str = ", ".join(cols)
                stmt = text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols_str});")
                conn.execute(stmt)
                created += 1
            trans.commit()
            print(f"Successfully created/verified {created} performance indexes.")
        except Exception as e:
            trans.rollback()
            print(f"Error creating indexes: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    create_performance_indexes()
