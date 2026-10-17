-- ============================================================================
-- BẢN TỔNG HỢP SQL TOÀN DIỆN CHO CÁC TÍNH NĂNG & CODE MỚI TRÊN SUPABASE
-- Chạy an toàn trên Supabase SQL Editor (Idempotent - không làm mất dữ liệu cũ)
-- ============================================================================

-- Kích hoạt extension hỗ trợ exclusion constraint (chống trùng lịch)
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ============================================================================
-- PHẦN 1: TẠO CÁC BẢNG NẾU CHƯA TỒN TẠI (CREATE TABLE IF NOT EXISTS)
-- ============================================================================
-- Bảng: "user"
CREATE TABLE IF NOT EXISTS "user" (
	id SERIAL NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	phone VARCHAR(20), 
	role VARCHAR(20) NOT NULL, 
	admin_role VARCHAR(50), 
	is_admin BOOLEAN, 
	is_active BOOLEAN, 
	email_verified BOOLEAN, 
	verified_at TIMESTAMP WITHOUT TIME ZONE, 
	avatar VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

-- Bảng: "translator_profile"
CREATE TABLE IF NOT EXISTS translator_profile (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(200), 
	bio TEXT, 
	languages VARCHAR(300), 
	badges VARCHAR(200), 
	rating FLOAT, 
	total_reviews INTEGER, 
	total_jobs INTEGER, 
	response_time VARCHAR(50), 
	is_verified BOOLEAN, 
	certificates TEXT, 
	is_public BOOLEAN, 
	is_cv_public BOOLEAN, 
	source_language VARCHAR(100), 
	target_language VARCHAR(100), 
	interpreting_direction VARCHAR(50), 
	language_proficiency VARCHAR(50), 
	specializations TEXT, 
	interpreting_types TEXT, 
	work_modes VARCHAR(255), 
	education_level VARCHAR(100), 
	university VARCHAR(255), 
	major VARCHAR(255), 
	cert_name VARCHAR(255), 
	cert_year INTEGER, 
	experience_years INTEGER, 
	current_position VARCHAR(255), 
	notable_clients TEXT, 
	featured_projects TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

-- Bảng: "translator_preference"
CREATE TABLE IF NOT EXISTS translator_preference (
	id SERIAL NOT NULL, 
	translator_id INTEGER NOT NULL, 
	languages TEXT, 
	language_pairs TEXT, 
	service_types TEXT, 
	specialties TEXT, 
	city VARCHAR(100), 
	work_mode VARCHAR(20), 
	offers_certified BOOLEAN, 
	notify_new_jobs BOOLEAN, 
	notify_messages BOOLEAN, 
	notify_contracts BOOLEAN, 
	notify_reviews BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (translator_id), 
	FOREIGN KEY(translator_id) REFERENCES "user" (id)
);

-- Bảng: "hirer_profile"
CREATE TABLE IF NOT EXISTS hirer_profile (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(100), 
	company VARCHAR(200), 
	location VARCHAR(100), 
	rating FLOAT, 
	account_type VARCHAR(20), 
	tax_code VARCHAR(13), 
	industry TEXT, 
	company_size VARCHAR(20), 
	address VARCHAR(300), 
	company_email VARCHAR(150), 
	website VARCHAR(300), 
	hotline VARCHAR(30), 
	rep_name VARCHAR(100), 
	about TEXT, 
	hiring_field TEXT, 
	hiring_languages TEXT, 
	hiring_services TEXT, 
	contact_phone VARCHAR(30), 
	logo TEXT, 
	total_reviews INTEGER, 
	is_verified BOOLEAN, 
	verification_status VARCHAR(20), 
	verified_at TIMESTAMP WITHOUT TIME ZONE, 
	bank_name VARCHAR(100), 
	bank_account_number VARCHAR(50), 
	authorization_doc_url VARCHAR(500), 
	verification_checklist_data TEXT, 
	rejection_reason TEXT, 
	work_mode VARCHAR(20), 
	hiring_frequency VARCHAR(20), 
	typical_budget_min INTEGER, 
	typical_budget_max INTEGER, 
	needs_nda BOOLEAN, 
	needs_certified BOOLEAN, 
	special_requirements TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

-- Bảng: "service"
CREATE TABLE IF NOT EXISTS service (
	id SERIAL NOT NULL, 
	profile_id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	description TEXT, 
	languages VARCHAR(100), 
	category VARCHAR(100), 
	basic_price INTEGER NOT NULL, 
	standard_price INTEGER, 
	premium_price INTEGER, 
	basic_delivery VARCHAR(50), 
	standard_delivery VARCHAR(50), 
	premium_delivery VARCHAR(50), 
	PRIMARY KEY (id), 
	FOREIGN KEY(profile_id) REFERENCES translator_profile (id)
);

-- Bảng: "job"
CREATE TABLE IF NOT EXISTS job (
	id SERIAL NOT NULL, 
	hirer_id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(100), 
	category_group VARCHAR(50), 
	service_type VARCHAR(100), 
	source_lang VARCHAR(50), 
	target_lang VARCHAR(50), 
	budget_type VARCHAR(20), 
	budget_min INTEGER, 
	budget_max INTEGER, 
	event_date VARCHAR(100), 
	event_time_start VARCHAR(10), 
	event_time_end VARCHAR(10), 
	event_location VARCHAR(200), 
	deadline DATE, 
	status VARCHAR(20), 
	is_flagged BOOLEAN, 
	moderation_status VARCHAR(20), 
	moderation_checklist_data TEXT, 
	moderation_notes TEXT, 
	moderated_at TIMESTAMP WITHOUT TIME ZONE, 
	moderated_by INTEGER, 
	submission_version INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(hirer_id) REFERENCES "user" (id), 
	FOREIGN KEY(moderated_by) REFERENCES "user" (id)
);

-- Bảng: "job_schedule"
CREATE TABLE IF NOT EXISTS job_schedule (
	id SERIAL NOT NULL, 
	job_id INTEGER NOT NULL, 
	scheduled_date DATE NOT NULL, 
	start_time VARCHAR(10) NOT NULL, 
	end_time VARCHAR(10) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_id) REFERENCES job (id) ON DELETE CASCADE
);

-- Bảng: "proposal"
CREATE TABLE IF NOT EXISTS proposal (
	id SERIAL NOT NULL, 
	job_id INTEGER NOT NULL, 
	translator_id INTEGER NOT NULL, 
	cover_letter TEXT, 
	price INTEGER NOT NULL, 
	time_estimate VARCHAR(100), 
	status VARCHAR(20), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_proposal_job_translator UNIQUE (job_id, translator_id), 
	FOREIGN KEY(job_id) REFERENCES job (id), 
	FOREIGN KEY(translator_id) REFERENCES "user" (id)
);

-- Bảng: "contract"
CREATE TABLE IF NOT EXISTS contract (
	id SERIAL NOT NULL, 
	job_id INTEGER, 
	service_id INTEGER, 
	proposal_id INTEGER, 
	hirer_id INTEGER NOT NULL, 
	translator_id INTEGER NOT NULL, 
	agreed_price INTEGER NOT NULL, 
	scheduled_date VARCHAR(100), 
	scheduled_time_start VARCHAR(10), 
	scheduled_time_end VARCHAR(10), 
	location VARCHAR(200), 
	status VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_contract_job UNIQUE (job_id), 
	FOREIGN KEY(job_id) REFERENCES job (id), 
	FOREIGN KEY(service_id) REFERENCES service (id), 
	FOREIGN KEY(proposal_id) REFERENCES proposal (id), 
	FOREIGN KEY(hirer_id) REFERENCES "user" (id), 
	FOREIGN KEY(translator_id) REFERENCES "user" (id)
);

-- Bảng: "message"
CREATE TABLE IF NOT EXISTS message (
	id SERIAL NOT NULL, 
	contract_id INTEGER NOT NULL, 
	sender_id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	image_url TEXT, 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id)
);

-- Bảng: "direct_message"
CREATE TABLE IF NOT EXISTS direct_message (
	id SERIAL NOT NULL, 
	sender_id INTEGER NOT NULL, 
	receiver_id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	image_url TEXT, 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id), 
	FOREIGN KEY(receiver_id) REFERENCES "user" (id)
);

-- Bảng: "deliverable"
CREATE TABLE IF NOT EXISTS deliverable (
	id SERIAL NOT NULL, 
	contract_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	filepath VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id)
);

-- Bảng: "review"
CREATE TABLE IF NOT EXISTS review (
	id SERIAL NOT NULL, 
	contract_id INTEGER NOT NULL, 
	reviewer_id INTEGER NOT NULL, 
	reviewee_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	comment TEXT, 
	is_hidden BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_review_contract_reviewer UNIQUE (contract_id, reviewer_id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id), 
	FOREIGN KEY(reviewer_id) REFERENCES "user" (id), 
	FOREIGN KEY(reviewee_id) REFERENCES "user" (id)
);

-- Bảng: "notification"
CREATE TABLE IF NOT EXISTS notification (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	url VARCHAR(500), 
	is_read BOOLEAN, 
	related_job_id INTEGER, 
	related_contract_id INTEGER, 
	related_review_id INTEGER, 
	related_proposal_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(related_job_id) REFERENCES job (id), 
	FOREIGN KEY(related_contract_id) REFERENCES contract (id), 
	FOREIGN KEY(related_review_id) REFERENCES review (id), 
	FOREIGN KEY(related_proposal_id) REFERENCES proposal (id)
);

-- Bảng: "translator_schedule"
CREATE TABLE IF NOT EXISTS translator_schedule (
	id SERIAL NOT NULL, 
	translator_id INTEGER NOT NULL, 
	contract_id INTEGER, 
	job_id INTEGER, 
	service_id INTEGER, 
	scheduled_date DATE NOT NULL, 
	start_time TIME WITHOUT TIME ZONE NOT NULL, 
	end_time TIME WITHOUT TIME ZONE NOT NULL, 
	buffer_before_minutes INTEGER, 
	buffer_after_minutes INTEGER, 
	status VARCHAR(20), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(translator_id) REFERENCES "user" (id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id), 
	FOREIGN KEY(job_id) REFERENCES job (id), 
	FOREIGN KEY(service_id) REFERENCES service (id)
);

-- Bảng: "report"
CREATE TABLE IF NOT EXISTS report (
	id SERIAL NOT NULL, 
	reporter_id INTEGER NOT NULL, 
	target_type VARCHAR(50) NOT NULL, 
	target_id INTEGER NOT NULL, 
	reason VARCHAR(255) NOT NULL, 
	description TEXT, 
	evidence_url VARCHAR(500), 
	status VARCHAR(20), 
	related_job_id INTEGER, 
	related_contract_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reporter_id) REFERENCES "user" (id), 
	FOREIGN KEY(related_job_id) REFERENCES job (id), 
	FOREIGN KEY(related_contract_id) REFERENCES contract (id)
);

-- Bảng: "payment_transaction"
CREATE TABLE IF NOT EXISTS payment_transaction (
	id SERIAL NOT NULL, 
	contract_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	amount INTEGER NOT NULL, 
	status VARCHAR(20), 
	payment_method VARCHAR(50), 
	transaction_ref VARCHAR(100), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

-- Bảng: "admin_notification"
CREATE TABLE IF NOT EXISTS admin_notification (
	id SERIAL NOT NULL, 
	type VARCHAR(50) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	url VARCHAR(500), 
	is_read BOOLEAN, 
	related_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

-- Bảng: "login_attempt"
CREATE TABLE IF NOT EXISTS login_attempt (
	id SERIAL NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	ip_address VARCHAR(64), 
	success BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

-- Bảng: "admin_audit_log"
CREATE TABLE IF NOT EXISTS admin_audit_log (
	id SERIAL NOT NULL, 
	admin_id INTEGER, 
	action VARCHAR(50) NOT NULL, 
	target_type VARCHAR(50), 
	target_id INTEGER, 
	description TEXT, 
	ip_address VARCHAR(64), 
	user_agent VARCHAR(512), 
	extra_data TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(admin_id) REFERENCES "user" (id)
);

-- Bảng: "translator_verification"
CREATE TABLE IF NOT EXISTS translator_verification (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	cv_filename VARCHAR(255), 
	cv_url VARCHAR(500), 
	certificate_filename VARCHAR(255), 
	certificate_url VARCHAR(500), 
	id_card_filename VARCHAR(255), 
	id_card_url VARCHAR(500), 
	certificate_type VARCHAR(100), 
	certificate_name VARCHAR(255), 
	primary_language VARCHAR(100), 
	experience_years INTEGER, 
	notes TEXT, 
	current_step INTEGER, 
	draft_data TEXT, 
	full_name VARCHAR(100), 
	phone VARCHAR(20), 
	gender VARCHAR(20), 
	dob VARCHAR(20), 
	location VARCHAR(100), 
	bio TEXT, 
	source_language VARCHAR(100), 
	target_language VARCHAR(100), 
	interpreting_direction VARCHAR(50), 
	language_proficiency VARCHAR(50), 
	specializations TEXT, 
	interpreting_types TEXT, 
	education_level VARCHAR(100), 
	university VARCHAR(255), 
	major VARCHAR(255), 
	cert_year INTEGER, 
	current_position VARCHAR(255), 
	notable_clients TEXT, 
	featured_projects TEXT, 
	status VARCHAR(20), 
	rejection_reason TEXT, 
	reviewed_by INTEGER, 
	reviewed_at TIMESTAMP WITHOUT TIME ZONE, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE, 
	submission_version INTEGER, 
	submitted_snapshot TEXT, 
	checklist_data TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(reviewed_by) REFERENCES "user" (id)
);

-- Bảng: "verification_document"
CREATE TABLE IF NOT EXISTS verification_document (
	id SERIAL NOT NULL, 
	verification_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	document_type VARCHAR(50) NOT NULL, 
	original_filename VARCHAR(255) NOT NULL, 
	stored_filename VARCHAR(255) NOT NULL, 
	storage_provider VARCHAR(50), 
	storage_path VARCHAR(500) NOT NULL, 
	file_size INTEGER NOT NULL, 
	mime_type VARCHAR(100) NOT NULL, 
	file_extension VARCHAR(20) NOT NULL, 
	file_hash VARCHAR(64), 
	status VARCHAR(30), 
	review_notes TEXT, 
	reviewed_by INTEGER, 
	reviewed_at TIMESTAMP WITHOUT TIME ZONE, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(verification_id) REFERENCES translator_verification (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id), 
	FOREIGN KEY(reviewed_by) REFERENCES "user" (id)
);

-- Bảng: "verification_submission_version"
CREATE TABLE IF NOT EXISTS verification_submission_version (
	id SERIAL NOT NULL, 
	verification_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	version_number INTEGER NOT NULL, 
	status VARCHAR(20), 
	snapshot_data TEXT NOT NULL, 
	submitted_at TIMESTAMP WITHOUT TIME ZONE, 
	ip_address VARCHAR(50), 
	user_agent VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(verification_id) REFERENCES translator_verification (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

-- Bảng: "password_reset_token"
CREATE TABLE IF NOT EXISTS password_reset_token (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_used BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

-- Bảng: "email_verification_token"
CREATE TABLE IF NOT EXISTS email_verification_token (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_used BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

-- ============================================================================
-- PHẦN 2: BỔ SUNG CỘT MỚI VÀO CÁC BẢNG HIỆN CÓ (ALTER TABLE ADD COLUMN IF NOT EXISTS)
-- (Đảm bảo nếu bảng đã tồn tại từ trước thì không bị thiếu bất kỳ cột nào)
-- ============================================================================

-- Cập nhật cột cho bảng: "user"
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

-- Cập nhật cột cho bảng: "translator_profile"
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
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "is_public" BOOLEAN DEFAULT TRUE;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "is_cv_public" BOOLEAN DEFAULT FALSE;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "source_language" VARCHAR(100);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "target_language" VARCHAR(100);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "interpreting_direction" VARCHAR(50);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "language_proficiency" VARCHAR(50);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "specializations" TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "interpreting_types" TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "work_modes" VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "education_level" VARCHAR(100);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "university" VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "major" VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "cert_name" VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "cert_year" INTEGER;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "experience_years" INTEGER DEFAULT 0;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "current_position" VARCHAR(255);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "notable_clients" TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS "featured_projects" TEXT;

-- Cập nhật cột cho bảng: "translator_preference"
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

-- Cập nhật cột cho bảng: "hirer_profile"
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

-- Cập nhật cột cho bảng: "service"
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

-- Cập nhật cột cho bảng: "job"
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

-- Cập nhật cột cho bảng: "job_schedule"
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "job_id" INTEGER;
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "scheduled_date" DATE;
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "start_time" VARCHAR(10);
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "end_time" VARCHAR(10);
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "job_schedule" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "proposal"
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "job_id" INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "translator_id" INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "cover_letter" TEXT;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "price" INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "time_estimate" VARCHAR(100);
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "contract"
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

-- Cập nhật cột cho bảng: "message"
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "sender_id" INTEGER;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "content" TEXT;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "image_url" TEXT;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "direct_message"
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "sender_id" INTEGER;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "receiver_id" INTEGER;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "content" TEXT;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "image_url" TEXT;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "deliverable"
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "filename" VARCHAR(255);
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "filepath" VARCHAR(500);
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "review"
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "reviewer_id" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "reviewee_id" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "rating" INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "comment" TEXT;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "is_hidden" BOOLEAN DEFAULT FALSE;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "notification"
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

-- Cập nhật cột cho bảng: "translator_schedule"
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

-- Cập nhật cột cho bảng: "report"
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

-- Cập nhật cột cho bảng: "payment_transaction"
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "contract_id" INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "amount" INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "payment_method" VARCHAR(50);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "transaction_ref" VARCHAR(100);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS "updated_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "admin_notification"
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "type" VARCHAR(50);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "title" VARCHAR(255);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "message" TEXT;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "url" VARCHAR(500);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "is_read" BOOLEAN DEFAULT FALSE;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "related_id" INTEGER;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "login_attempt"
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "email" VARCHAR(120);
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "ip_address" VARCHAR(64);
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "success" BOOLEAN DEFAULT FALSE;
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "admin_audit_log"
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "admin_id" INTEGER;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "action" VARCHAR(50);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "target_type" VARCHAR(50);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "target_id" INTEGER;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "description" TEXT;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "ip_address" VARCHAR(64);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "user_agent" VARCHAR(512);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "extra_data" TEXT;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;

-- Cập nhật cột cho bảng: "translator_verification"
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

-- Cập nhật cột cho bảng: "verification_document"
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

-- Cập nhật cột cho bảng: "verification_submission_version"
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "verification_id" INTEGER;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "version_number" INTEGER DEFAULT 1;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "status" VARCHAR(20) DEFAULT 'pending';
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "snapshot_data" TEXT;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "submitted_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "ip_address" VARCHAR(50);
ALTER TABLE "verification_submission_version" ADD COLUMN IF NOT EXISTS "user_agent" VARCHAR(255);

-- Cập nhật cột cho bảng: "password_reset_token"
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "token_hash" VARCHAR(128);
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "expires_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "password_reset_token" ADD COLUMN IF NOT EXISTS "is_used" BOOLEAN DEFAULT FALSE;

-- Cập nhật cột cho bảng: "email_verification_token"
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "user_id" INTEGER;
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "token_hash" VARCHAR(128);
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "created_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "expires_at" TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "email_verification_token" ADD COLUMN IF NOT EXISTS "is_used" BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- PHẦN 3: ĐỒNG BỘ & CHUẨN HÓA DỮ LIỆU ĐANG CÓ (DATA BACKFILL & FIX)
-- ============================================================================

-- 1. Chuẩn hóa trạng thái kiểm duyệt tin đăng việc làm (Job Moderation)
UPDATE job SET moderation_status = 'flagged' WHERE is_flagged = TRUE AND (moderation_status IS NULL OR moderation_status = 'pending');
UPDATE job SET moderation_status = 'approved' WHERE (status IN ('open', 'contracted', 'completed') OR status IS NULL) AND (is_flagged = FALSE OR is_flagged IS NULL) AND moderation_status = 'pending';
UPDATE job SET submission_version = 1 WHERE submission_version IS NULL;

-- 2. Chuẩn hóa trạng thái xác minh nhà tuyển dụng (Hirer Verification)
UPDATE hirer_profile SET verification_status = 'verified' WHERE is_verified = TRUE AND (verification_status IS NULL OR verification_status = 'unverified');
UPDATE hirer_profile SET verification_status = 'unverified' WHERE (is_verified = FALSE OR is_verified IS NULL) AND verification_status IS NULL;

-- 3. Chuẩn hóa tài khoản người dùng (User Auth & Verification)
UPDATE "user" SET email_verified = TRUE WHERE (is_admin = TRUE OR email_verified IS NULL);
UPDATE "user" SET is_active = TRUE WHERE is_active IS NULL;

-- 4. Chuẩn hóa lịch phiên dịch (Translator Schedule)
UPDATE translator_schedule SET status = 'reserved' WHERE status IS NULL;
UPDATE translator_schedule SET buffer_before_minutes = 0 WHERE buffer_before_minutes IS NULL;
UPDATE translator_schedule SET buffer_after_minutes = 30 WHERE buffer_after_minutes IS NULL;

-- ============================================================================
-- PHẦN 4: CHỈ MỤC TỐI ƯU HÓA TRUY VẤN (INDEXES)
-- ============================================================================

CREATE INDEX IF NOT EXISTS ix_user_email ON "user" (email);
CREATE INDEX IF NOT EXISTS ix_user_role ON "user" (role);
CREATE INDEX IF NOT EXISTS ix_user_email_verified ON "user" (email_verified);
CREATE INDEX IF NOT EXISTS ix_user_is_active ON "user" (is_active);
CREATE INDEX IF NOT EXISTS ix_job_moderation_status ON job (moderation_status);
CREATE INDEX IF NOT EXISTS ix_job_status ON job (status);
CREATE INDEX IF NOT EXISTS ix_job_hirer_id ON job (hirer_id);
CREATE INDEX IF NOT EXISTS ix_job_created_at ON job (created_at);
CREATE INDEX IF NOT EXISTS ix_hirer_profile_verification_status ON hirer_profile (verification_status);
CREATE INDEX IF NOT EXISTS ix_hirer_profile_user_id ON hirer_profile (user_id);
CREATE INDEX IF NOT EXISTS ix_translator_profile_user_id ON translator_profile (user_id);
CREATE INDEX IF NOT EXISTS ix_translator_profile_is_verified ON translator_profile (is_verified);
CREATE INDEX IF NOT EXISTS ix_translator_verification_status ON translator_verification (status);
CREATE INDEX IF NOT EXISTS ix_translator_verification_user_id ON translator_verification (user_id);
CREATE INDEX IF NOT EXISTS ix_verification_document_verification_id ON verification_document (verification_id);
CREATE INDEX IF NOT EXISTS ix_verification_document_user_id ON verification_document (user_id);
CREATE INDEX IF NOT EXISTS ix_verification_document_stored_filename ON verification_document (stored_filename);
CREATE INDEX IF NOT EXISTS ix_verification_sub_ver_verification_id ON verification_submission_version (verification_id);
CREATE INDEX IF NOT EXISTS ix_translator_schedule_translator_id ON translator_schedule (translator_id);
CREATE INDEX IF NOT EXISTS ix_translator_schedule_scheduled_date ON translator_schedule (scheduled_date);
CREATE INDEX IF NOT EXISTS ix_translator_schedule_status ON translator_schedule (status);
CREATE INDEX IF NOT EXISTS ix_report_reporter_id ON report (reporter_id);
CREATE INDEX IF NOT EXISTS ix_report_status ON report (status);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_contract_id ON payment_transaction (contract_id);
CREATE INDEX IF NOT EXISTS ix_payment_transaction_status ON payment_transaction (status);
CREATE INDEX IF NOT EXISTS ix_admin_notification_is_read ON admin_notification (is_read);
CREATE INDEX IF NOT EXISTS ix_login_attempt_email ON login_attempt (email);
CREATE INDEX IF NOT EXISTS ix_admin_audit_log_admin_id ON admin_audit_log (admin_id);
CREATE INDEX IF NOT EXISTS ix_email_verification_token_user_id ON email_verification_token (user_id);
CREATE INDEX IF NOT EXISTS ix_password_reset_token_user_id ON password_reset_token (user_id);

-- ============================================================================
-- PHẦN 5: RÀNG BUỘC TOÀN VẸN & CHỐNG TRÙNG LỊCH (EXCLUSION CONSTRAINT)
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'no_overlapping_schedules' 
          AND conrelid = 'translator_schedule'::regclass
    ) THEN
        ALTER TABLE translator_schedule
        ADD CONSTRAINT no_overlapping_schedules
        EXCLUDE USING gist (
            translator_id WITH =,
            tsrange(
                (scheduled_date + start_time) - (COALESCE(buffer_before_minutes, 0) * interval '1 minute'),
                (scheduled_date + end_time) + (COALESCE(buffer_after_minutes, 30) * interval '1 minute')
            ) WITH &&
        )
        WHERE (status IN ('reserved', 'active'));
    END IF;
END $$;

-- Hoàn tất cập nhật