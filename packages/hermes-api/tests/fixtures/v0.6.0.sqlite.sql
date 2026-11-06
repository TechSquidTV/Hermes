-- Created with original v0.6.0 migrations at 29ddeaee16f0a1b53ba6a27ce8027b03235e2fea; synthetic data only.
BEGIN TRANSACTION;
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO "alembic_version" VALUES('d5e92b7f3a1c');
CREATE TABLE api_keys (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	key_hash VARCHAR NOT NULL, 
	permissions JSON NOT NULL, 
	rate_limit INTEGER NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_used DATETIME, 
	expires_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (key_hash)
);
CREATE TABLE batch_videos (
	id VARCHAR NOT NULL, 
	batch_id VARCHAR NOT NULL, 
	video_url TEXT NOT NULL, 
	video_id VARCHAR(200), 
	title VARCHAR(500), 
	duration INTEGER, 
	thumbnail_url TEXT, 
	uploader VARCHAR(200), 
	view_count INTEGER, 
	upload_date VARCHAR(8), 
	position INTEGER NOT NULL, 
	status VARCHAR(11) NOT NULL, 
	download_id VARCHAR, 
	error_message TEXT, 
	retry_count INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES download_batches (id) ON DELETE CASCADE, 
	FOREIGN KEY(download_id) REFERENCES downloads (id) ON DELETE SET NULL
);
CREATE TABLE download_batches (
	id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	batch_type VARCHAR(12) NOT NULL, 
	batch_title VARCHAR(500), 
	source_url TEXT, 
	status VARCHAR(10) NOT NULL, 
	total_videos INTEGER NOT NULL, 
	completed_videos INTEGER NOT NULL, 
	failed_videos INTEGER NOT NULL, 
	overall_progress FLOAT NOT NULL, 
	playlist_id VARCHAR(200), 
	playlist_uploader VARCHAR(200), 
	created_at DATETIME NOT NULL, 
	started_at DATETIME, 
	completed_at DATETIME, 
	format_spec VARCHAR(100), 
	output_directory TEXT, 
	celery_task_id VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE TABLE download_files (
	id VARCHAR NOT NULL, 
	download_id VARCHAR NOT NULL, 
	filename VARCHAR NOT NULL, 
	filepath VARCHAR NOT NULL, 
	file_size INTEGER NOT NULL, 
	file_type VARCHAR NOT NULL, 
	format_id VARCHAR, 
	resolution VARCHAR, 
	codec VARCHAR, 
	bitrate INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(download_id) REFERENCES downloads (id) ON DELETE CASCADE
);
INSERT INTO "download_files" VALUES('legacy-file','legacy-download','legacy.mp4','downloads/legacy.mp4',12,'video',NULL,NULL,NULL,NULL,'2026-01-01');
CREATE TABLE download_history (
	id VARCHAR NOT NULL, 
	download_id VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	status VARCHAR(9) NOT NULL, 
	duration FLOAT, 
	file_size INTEGER, 
	error_message TEXT, 
	video_id VARCHAR, 
	extractor VARCHAR, 
	format_used VARCHAR, 
	started_at DATETIME NOT NULL, 
	completed_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE TABLE downloads (
	id VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	title VARCHAR, 
	status VARCHAR(11) NOT NULL, 
	progress FLOAT, 
	downloaded_bytes INTEGER, 
	total_bytes INTEGER, 
	download_speed FLOAT, 
	eta FLOAT, 
	format_spec VARCHAR, 
	output_path VARCHAR, 
	file_size INTEGER, 
	duration FLOAT, 
	error_message TEXT, 
	video_id VARCHAR, 
	extractor VARCHAR, 
	thumbnail_url VARCHAR, 
	description TEXT, 
	batch_id VARCHAR, 
	batch_position INTEGER, 
	batch_video_id VARCHAR(200), 
	created_at DATETIME NOT NULL, 
	started_at DATETIME, 
	completed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(batch_id) REFERENCES download_batches (id) ON DELETE SET NULL
);
INSERT INTO "downloads" VALUES('legacy-download','https://example.com/legacy',NULL,'completed',100.0,NULL,NULL,NULL,NULL,NULL,'downloads/legacy.mp4',12,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,'2026-01-01',NULL,'2026-01-01');
CREATE TABLE system_settings (
	id INTEGER NOT NULL, 
	allow_public_signup BOOLEAN DEFAULT '1' NOT NULL, 
	updated_by_user_id VARCHAR, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "system_settings" VALUES(1,1,NULL,'2026-11-06T15:44:34.501740+00:00');
CREATE TABLE token_blacklist (
	id VARCHAR NOT NULL, 
	token_id VARCHAR NOT NULL, 
	user_id VARCHAR NOT NULL, 
	expires_at DATETIME NOT NULL, 
	reason VARCHAR NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	UNIQUE (token_id)
);
CREATE TABLE users (
	id VARCHAR NOT NULL, 
	username VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	password_hash VARCHAR NOT NULL, 
	avatar VARCHAR, 
	is_active BOOLEAN NOT NULL, 
	preferences JSON, 
	created_at DATETIME NOT NULL, 
	last_login DATETIME, is_admin BOOLEAN DEFAULT '0' NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email)
);
INSERT INTO "users" VALUES('legacy-admin','legacy-admin','legacy@example.com','unused',NULL,1,NULL,'2026-01-01',NULL,1);
CREATE TABLE webhooks (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	url VARCHAR NOT NULL, 
	secret VARCHAR, 
	events JSON NOT NULL, 
	headers JSON, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	last_triggered DATETIME, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_users_id ON users (id);
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_download_batches_id ON download_batches (id);
CREATE INDEX ix_download_batches_user_id ON download_batches (user_id);
CREATE INDEX ix_download_batches_status ON download_batches (status);
CREATE INDEX ix_download_batches_created_at ON download_batches (created_at);
CREATE INDEX ix_downloads_id ON downloads (id);
CREATE INDEX ix_downloads_url ON downloads (url);
CREATE INDEX ix_downloads_video_id ON downloads (video_id);
CREATE INDEX ix_downloads_batch_id ON downloads (batch_id);
CREATE INDEX ix_batch_videos_id ON batch_videos (id);
CREATE INDEX ix_batch_videos_batch_id ON batch_videos (batch_id);
CREATE INDEX ix_batch_videos_status ON batch_videos (status);
CREATE INDEX ix_batch_videos_download_id ON batch_videos (download_id);
CREATE INDEX ix_download_files_id ON download_files (id);
CREATE INDEX ix_webhooks_id ON webhooks (id);
CREATE INDEX ix_api_keys_id ON api_keys (id);
CREATE INDEX ix_api_keys_user_id ON api_keys (user_id);
CREATE INDEX ix_download_history_id ON download_history (id);
CREATE INDEX ix_download_history_download_id ON download_history (download_id);
CREATE INDEX ix_token_blacklist_id ON token_blacklist (id);
CREATE UNIQUE INDEX ix_token_blacklist_token_id ON token_blacklist (token_id);
CREATE INDEX ix_token_blacklist_user_id ON token_blacklist (user_id);
CREATE INDEX ix_token_blacklist_expires_at ON token_blacklist (expires_at);
CREATE INDEX ix_users_is_admin ON users (is_admin);
COMMIT;
