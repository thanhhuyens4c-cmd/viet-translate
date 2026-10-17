-- Auto-generated complete idempotent migration script for Supabase PostgreSQL
-- Run this script in Supabase SQL Editor to guarantee all columns are synced.

-- ========================================================
-- Table: "user"
-- ========================================================
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "name" VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "email" VARCHAR(120);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "password_hash" VARCHAR(256);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "phone" VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "role" VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "admin_role" VARCHAR(50);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "is_admin" BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "is_active" BOOLEAN DEFAULT TRUE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "email_verified" BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "verified_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "avatar" VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "translator_profile"
-- ========================================================
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "title" VARCHAR(200);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "bio" TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "languages" VARCHAR(300);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "badges" VARCHAR(200);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "rating" FLOAT DEFAULT 0.0;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "total_reviews" INTEGER DEFAULT 0;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "total_jobs" INTEGER DEFAULT 0;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "response_time" VARCHAR(50) DEFAULT '2 giờ';
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "is_verified" BOOLEAN DEFAULT FALSE;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "certificates" TEXT;

-- ========================================================
-- Table: "translator_preference"
-- ========================================================
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "translator_id" INTEGER;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "languages" TEXT DEFAULT '';
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "language_pairs" TEXT DEFAULT '';
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "service_types" TEXT DEFAULT '';
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "specialties" TEXT DEFAULT '';
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "city" VARCHAR(100);
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "work_mode" VARCHAR(20);
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "offers_certified" BOOLEAN DEFAULT FALSE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "notify_new_jobs" BOOLEAN DEFAULT TRUE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "notify_messages" BOOLEAN DEFAULT TRUE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "notify_contracts" BOOLEAN DEFAULT TRUE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "notify_reviews" BOOLEAN DEFAULT TRUE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "hirer_profile"
-- ========================================================
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "title" VARCHAR(100);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "company" VARCHAR(200);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "location" VARCHAR(100);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "rating" FLOAT DEFAULT 0.0;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "account_type" VARCHAR(20) DEFAULT 'individual';
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "tax_code" VARCHAR(13);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "industry" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "company_size" VARCHAR(20);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "address" VARCHAR(300);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "company_email" VARCHAR(150);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "website" VARCHAR(300);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "hotline" VARCHAR(30);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "rep_name" VARCHAR(100);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "about" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "hiring_field" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "hiring_languages" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "hiring_services" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "contact_phone" VARCHAR(30);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "logo" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "total_reviews" INTEGER DEFAULT 0;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "is_verified" BOOLEAN DEFAULT FALSE;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "verification_status" VARCHAR(20) DEFAULT 'unverified';
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "verified_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "bank_name" VARCHAR(100);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "bank_account_number" VARCHAR(50);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "authorization_doc_url" VARCHAR(500);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "verification_checklist_data" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "rejection_reason" TEXT;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "work_mode" VARCHAR(20);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "hiring_frequency" VARCHAR(20);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "typical_budget_min" INTEGER;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "typical_budget_max" INTEGER;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "needs_nda" BOOLEAN DEFAULT FALSE;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "needs_certified" BOOLEAN DEFAULT FALSE;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS "special_requirements" TEXT;

-- ========================================================
-- Table: "service"
-- ========================================================
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "profile_id" INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "name" VARCHAR(200);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "description" TEXT;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "languages" VARCHAR(100);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "category" VARCHAR(100);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "basic_price" INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "standard_price" INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "premium_price" INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "basic_delivery" VARCHAR(50) DEFAULT '3 ngày';
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "standard_delivery" VARCHAR(50) DEFAULT '2 ngày';
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS "premium_delivery" VARCHAR(50) DEFAULT '1 ngày';

-- ========================================================
-- Table: "job"
-- ========================================================
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "hirer_id" INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "title" VARCHAR(200);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "description" TEXT;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "category" VARCHAR(100);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "category_group" VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "service_type" VARCHAR(100);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "source_lang" VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "target_lang" VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "budget_type" VARCHAR(20);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "budget_min" INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "budget_max" INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "event_date" VARCHAR(100);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "event_time_start" VARCHAR(10);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "event_time_end" VARCHAR(10);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "event_location" VARCHAR(200);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "deadline" DATE;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'open';
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "is_flagged" BOOLEAN DEFAULT FALSE;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "moderation_status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "moderation_checklist_data" TEXT;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "moderation_notes" TEXT;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "moderated_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "moderated_by" INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "submission_version" INTEGER DEFAULT 1;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "job_schedule"
-- ========================================================
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "job_id" INTEGER;
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "scheduled_date" DATE;
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "start_time" VARCHAR(10);
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "end_time" VARCHAR(10);
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "proposal"
-- ========================================================
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "job_id" INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "translator_id" INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "cover_letter" TEXT;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "price" INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "time_estimate" VARCHAR(100);
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "contract"
-- ========================================================
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "job_id" INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "service_id" INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "proposal_id" INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "hirer_id" INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "translator_id" INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "agreed_price" INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "scheduled_date" VARCHAR(100);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "scheduled_time_start" VARCHAR(10);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "scheduled_time_end" VARCHAR(10);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "location" VARCHAR(200);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "status" VARCHAR(50) DEFAULT 'escrow_pending';
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "message"
-- ========================================================
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "sender_id" INTEGER;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "content" TEXT;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "image_url" TEXT;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "direct_message"
-- ========================================================
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "sender_id" INTEGER;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "receiver_id" INTEGER;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "content" TEXT;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "image_url" TEXT;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "deliverable"
-- ========================================================
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "filename" VARCHAR(255);
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "filepath" VARCHAR(500);
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "review"
-- ========================================================
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "reviewer_id" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "reviewee_id" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "rating" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "comment" TEXT;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "is_hidden" BOOLEAN DEFAULT FALSE;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "notification"
-- ========================================================
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "type" VARCHAR(50);
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "title" VARCHAR(255);
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "message" TEXT;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "url" VARCHAR(500);
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "related_job_id" INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "related_contract_id" INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "related_review_id" INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "related_proposal_id" INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "translator_schedule"
-- ========================================================
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "translator_id" INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "job_id" INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "service_id" INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "scheduled_date" DATE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "start_time" TIME WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "end_time" TIME WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "buffer_before_minutes" INTEGER DEFAULT 0;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "buffer_after_minutes" INTEGER DEFAULT 30;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'reserved';
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS "expires_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "report"
-- ========================================================
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "reporter_id" INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "target_type" VARCHAR(50);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "target_id" INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "reason" VARCHAR(255);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "description" TEXT;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "evidence_url" VARCHAR(500);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'new';
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "related_job_id" INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "related_contract_id" INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "payment_transaction"
-- ========================================================
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "amount" INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "payment_method" VARCHAR(50);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "transaction_ref" VARCHAR(100);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "admin_notification"
-- ========================================================
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "type" VARCHAR(50);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "title" VARCHAR(255);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "message" TEXT;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "url" VARCHAR(500);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "related_id" INTEGER;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "login_attempt"
-- ========================================================
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "email" VARCHAR(120);
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "ip_address" VARCHAR(64);
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "success" BOOLEAN DEFAULT FALSE;
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "admin_audit_log"
-- ========================================================
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "admin_id" INTEGER;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "action" VARCHAR(50);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "target_type" VARCHAR(50);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "target_id" INTEGER;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "description" TEXT;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "ip_address" VARCHAR(64);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "user_agent" VARCHAR(512);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "extra_data" TEXT;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "translator_verification"
-- ========================================================
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "cv_filename" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "cv_url" VARCHAR(500);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "certificate_filename" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "certificate_url" VARCHAR(500);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "id_card_filename" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "id_card_url" VARCHAR(500);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "certificate_type" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "certificate_name" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "primary_language" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "experience_years" INTEGER DEFAULT 0;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "notes" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "current_step" INTEGER DEFAULT 1;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "draft_data" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "full_name" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "phone" VARCHAR(20);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "gender" VARCHAR(20);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "dob" VARCHAR(20);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "location" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "bio" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "source_language" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "target_language" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "interpreting_direction" VARCHAR(50);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "language_proficiency" VARCHAR(50);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "specializations" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "interpreting_types" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "education_level" VARCHAR(100);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "university" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "major" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "cert_year" INTEGER;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "current_position" VARCHAR(255);
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "notable_clients" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "featured_projects" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'draft';
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "rejection_reason" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "reviewed_by" INTEGER;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "reviewed_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "submitted_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "submission_version" INTEGER DEFAULT 0;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "submitted_snapshot" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "checklist_data" TEXT;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_verification" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "verification_document"
-- ========================================================
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "verification_id" INTEGER;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "document_type" VARCHAR(50);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "original_filename" VARCHAR(255);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "stored_filename" VARCHAR(255);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "storage_provider" VARCHAR(50) DEFAULT 'local_private';
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "storage_path" VARCHAR(500);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "file_size" INTEGER DEFAULT 0;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "mime_type" VARCHAR(100);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "file_extension" VARCHAR(20);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "file_hash" VARCHAR(64);
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "status" VARCHAR(30) DEFAULT 'uploaded';
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "review_notes" TEXT;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "reviewed_by" INTEGER;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "reviewed_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "is_active" BOOLEAN DEFAULT TRUE;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "verification_document" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- ========================================================
-- Table: "verification_submission_version"
-- ========================================================
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "verification_id" INTEGER;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "version_number" INTEGER DEFAULT 1;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "snapshot_data" TEXT;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "submitted_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "ip_address" VARCHAR(50);
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "user_agent" VARCHAR(255);

-- ========================================================
-- Table: "password_reset_token"
-- ========================================================
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "token_hash" VARCHAR(128);
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "expires_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "is_used" BOOLEAN DEFAULT FALSE;

-- ========================================================
-- Table: "email_verification_token"
-- ========================================================
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "token_hash" VARCHAR(128);
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "expires_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "is_used" BOOLEAN DEFAULT FALSE;
