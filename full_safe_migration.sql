-- 1. TẠO CÁC BẢNG NẾU CHƯA CÓ (Tự động)
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
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

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
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

CREATE TABLE IF NOT EXISTS translator_preference (
	id SERIAL NOT NULL, 
	translator_id INTEGER NOT NULL, 
	languages TEXT, 
	language_pairs TEXT, 
	service_types TEXT, 
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

CREATE TABLE IF NOT EXISTS hirer_profile (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(100), 
	company VARCHAR(200), 
	location VARCHAR(100), 
	rating FLOAT, 
	PRIMARY KEY (id), 
	UNIQUE (user_id), 
	FOREIGN KEY(user_id) REFERENCES "user" (id)
);

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
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(hirer_id) REFERENCES "user" (id)
);

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

CREATE TABLE IF NOT EXISTS message (
	id SERIAL NOT NULL, 
	contract_id INTEGER NOT NULL, 
	sender_id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id)
);

CREATE TABLE IF NOT EXISTS direct_message (
	id SERIAL NOT NULL, 
	sender_id INTEGER NOT NULL, 
	receiver_id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES "user" (id), 
	FOREIGN KEY(receiver_id) REFERENCES "user" (id)
);

CREATE TABLE IF NOT EXISTS deliverable (
	id SERIAL NOT NULL, 
	contract_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	filepath VARCHAR(500) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id)
);

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
	UNIQUE (contract_id), 
	FOREIGN KEY(contract_id) REFERENCES contract (id), 
	FOREIGN KEY(job_id) REFERENCES job (id), 
	FOREIGN KEY(service_id) REFERENCES service (id)
);

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

CREATE TABLE IF NOT EXISTS login_attempt (
	id SERIAL NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	ip_address VARCHAR(64), 
	success BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

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

-- 2. THÊM TẤT CẢ CÁC CỘT (Nếu thiếu, bỏ qua nếu đã có)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS name VARCHAR(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email VARCHAR(120);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role VARCHAR(20);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS admin_role VARCHAR(50);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS avatar VARCHAR(255);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS title VARCHAR(200);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS languages VARCHAR(300);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS badges VARCHAR(200);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS rating FLOAT;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS total_reviews INTEGER;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS total_jobs INTEGER;
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS response_time VARCHAR(50);
ALTER TABLE "translator_profile" ADD COLUMN IF NOT EXISTS is_verified BOOLEAN;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS translator_id INTEGER;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS languages TEXT;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS language_pairs TEXT;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS service_types TEXT;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS notify_new_jobs BOOLEAN;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS notify_messages BOOLEAN;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS notify_contracts BOOLEAN;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS notify_reviews BOOLEAN;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_preference" ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS title VARCHAR(100);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS company VARCHAR(200);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS location VARCHAR(100);
ALTER TABLE "hirer_profile" ADD COLUMN IF NOT EXISTS rating FLOAT;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS profile_id INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS name VARCHAR(200);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS languages VARCHAR(100);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS category VARCHAR(100);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS basic_price INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS standard_price INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS premium_price INTEGER;
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS basic_delivery VARCHAR(50);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS standard_delivery VARCHAR(50);
ALTER TABLE "service" ADD COLUMN IF NOT EXISTS premium_delivery VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS hirer_id INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS title VARCHAR(200);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS category VARCHAR(100);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS category_group VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS service_type VARCHAR(100);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS source_lang VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS target_lang VARCHAR(50);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS budget_type VARCHAR(20);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS budget_min INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS budget_max INTEGER;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS event_date VARCHAR(100);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS event_time_start VARCHAR(10);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS event_time_end VARCHAR(10);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS event_location VARCHAR(200);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS deadline DATE;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS status VARCHAR(20);
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS is_flagged BOOLEAN;
ALTER TABLE "job" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS job_id INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS translator_id INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS cover_letter TEXT;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS price INTEGER;
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS time_estimate VARCHAR(100);
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS status VARCHAR(20);
ALTER TABLE "proposal" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS job_id INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS service_id INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS proposal_id INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS hirer_id INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS translator_id INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS agreed_price INTEGER;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS scheduled_date VARCHAR(100);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS scheduled_time_start VARCHAR(10);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS scheduled_time_end VARCHAR(10);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS location VARCHAR(200);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS status VARCHAR(50);
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "contract" ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS contract_id INTEGER;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS sender_id INTEGER;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS is_read BOOLEAN;
ALTER TABLE "message" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS sender_id INTEGER;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS receiver_id INTEGER;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS is_read BOOLEAN;
ALTER TABLE "direct_message" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS contract_id INTEGER;
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS filename VARCHAR(255);
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS filepath VARCHAR(500);
ALTER TABLE "deliverable" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS contract_id INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS reviewer_id INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS reviewee_id INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS rating INTEGER;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS comment TEXT;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN;
ALTER TABLE "review" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS type VARCHAR(50);
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS title VARCHAR(255);
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS url VARCHAR(500);
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS is_read BOOLEAN;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS related_job_id INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS related_contract_id INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS related_review_id INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS related_proposal_id INTEGER;
ALTER TABLE "notification" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS translator_id INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS contract_id INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS job_id INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS service_id INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS scheduled_date DATE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS start_time TIME WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS end_time TIME WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS buffer_before_minutes INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS buffer_after_minutes INTEGER;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS status VARCHAR(20);
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "translator_schedule" ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS reporter_id INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS target_type VARCHAR(50);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS target_id INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS reason VARCHAR(255);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS evidence_url VARCHAR(500);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS status VARCHAR(20);
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS related_job_id INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS related_contract_id INTEGER;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "report" ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS contract_id INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS user_id INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS amount INTEGER;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS status VARCHAR(20);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS transaction_ref VARCHAR(100);
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "payment_transaction" ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS type VARCHAR(50);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS title VARCHAR(255);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS url VARCHAR(500);
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS is_read BOOLEAN;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS related_id INTEGER;
ALTER TABLE "admin_notification" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS email VARCHAR(120);
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS ip_address VARCHAR(64);
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS success BOOLEAN;
ALTER TABLE "login_attempt" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS admin_id INTEGER;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS action VARCHAR(50);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS target_type VARCHAR(50);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS target_id INTEGER;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS ip_address VARCHAR(64);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS user_agent VARCHAR(512);
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS extra_data TEXT;
ALTER TABLE "admin_audit_log" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE;
