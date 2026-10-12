-- v2: seconds REAL -> UTC milliseconds INTEGER; transaction owned by runner.

CREATE TABLE ms_schema_migrations (
 version INTEGER PRIMARY KEY CHECK(version>0), checksum TEXT NOT NULL, applied_at INTEGER CHECK(applied_at IS NULL OR (typeof(applied_at)='integer' AND applied_at BETWEEN 0 AND 253402300799999)) NOT NULL, app_version TEXT NOT NULL);

INSERT INTO ms_schema_migrations (version,checksum,applied_at,app_version) SELECT version,checksum,school_seconds_to_ms(applied_at),app_version FROM schema_migrations;

CREATE TABLE ms_users (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), email_normalized TEXT NOT NULL UNIQUE CHECK(email_normalized=lower(trim(email_normalized))),
 email_display TEXT NOT NULL, display_name TEXT NOT NULL CHECK(length(display_name) BETWEEN 1 AND 80),
 password_hash TEXT NOT NULL CHECK(length(password_hash)>0),
 role TEXT NOT NULL CHECK(role IN ('DRIVER','ANALYST','ADMIN')),
 status TEXT NOT NULL CHECK(status IN ('PENDING_VERIFICATION','ACTIVE','BLOCKED')),
 verified_email_at INTEGER CHECK(verified_email_at IS NULL OR (typeof(verified_email_at)='integer' AND verified_email_at BETWEEN 0 AND 253402300799999)), security_version INTEGER NOT NULL DEFAULT 1 CHECK(security_version>=1),
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1), created_at INTEGER CHECK(created_at IS NULL OR (typeof(created_at)='integer' AND created_at BETWEEN 0 AND 253402300799999)) NOT NULL, updated_at INTEGER CHECK(updated_at IS NULL OR (typeof(updated_at)='integer' AND updated_at BETWEEN 0 AND 253402300799999)) NOT NULL,
 CHECK(status!='ACTIVE' OR verified_email_at IS NOT NULL));

INSERT INTO ms_users (id,email_normalized,email_display,display_name,password_hash,role,status,verified_email_at,security_version,revision,created_at,updated_at) SELECT id,email_normalized,email_display,display_name,password_hash,role,status,school_seconds_to_ms(verified_email_at),security_version,revision,school_seconds_to_ms(created_at),school_seconds_to_ms(updated_at) FROM users;

CREATE TABLE ms_browser_sessions (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), user_id TEXT NOT NULL REFERENCES ms_users(id), secret_hash TEXT CHECK(length(secret_hash)=64 AND secret_hash NOT GLOB '*[^0-9a-f]*') NOT NULL UNIQUE,
 csrf_hash TEXT CHECK(length(csrf_hash)=64 AND csrf_hash NOT GLOB '*[^0-9a-f]*') NOT NULL, security_version INTEGER NOT NULL CHECK(security_version>=1),
 authenticated_at INTEGER CHECK(authenticated_at IS NULL OR (typeof(authenticated_at)='integer' AND authenticated_at BETWEEN 0 AND 253402300799999)) NOT NULL, created_at INTEGER CHECK(created_at IS NULL OR (typeof(created_at)='integer' AND created_at BETWEEN 0 AND 253402300799999)) NOT NULL, last_activity_at INTEGER CHECK(last_activity_at IS NULL OR (typeof(last_activity_at)='integer' AND last_activity_at BETWEEN 0 AND 253402300799999)) NOT NULL,
 absolute_expiry INTEGER CHECK(absolute_expiry IS NULL OR (typeof(absolute_expiry)='integer' AND absolute_expiry BETWEEN 0 AND 253402300799999)) NOT NULL, revoked_at INTEGER CHECK(revoked_at IS NULL OR (typeof(revoked_at)='integer' AND revoked_at BETWEEN 0 AND 253402300799999)),
 CHECK(absolute_expiry>created_at AND absolute_expiry<=created_at+28800000),
 CHECK(last_activity_at>=created_at));

INSERT INTO ms_browser_sessions (id,user_id,secret_hash,csrf_hash,security_version,authenticated_at,created_at,last_activity_at,absolute_expiry,revoked_at) SELECT id,user_id,secret_hash,csrf_hash,security_version,school_seconds_to_ms(authenticated_at),school_seconds_to_ms(created_at),school_seconds_to_ms(last_activity_at),school_seconds_to_ms(absolute_expiry),school_seconds_to_ms(revoked_at) FROM browser_sessions;

CREATE TABLE ms_account_tokens (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), user_id TEXT NOT NULL REFERENCES ms_users(id), purpose TEXT NOT NULL CHECK(purpose IN ('RESET','VERIFY_EMAIL')),
 secret_hash TEXT CHECK(length(secret_hash)=64 AND secret_hash NOT GLOB '*[^0-9a-f]*') NOT NULL UNIQUE, security_version INTEGER NOT NULL CHECK(security_version>=1),
 issued_at INTEGER CHECK(issued_at IS NULL OR (typeof(issued_at)='integer' AND issued_at BETWEEN 0 AND 253402300799999)) NOT NULL, expiry INTEGER CHECK(expiry IS NULL OR (typeof(expiry)='integer' AND expiry BETWEEN 0 AND 253402300799999)) NOT NULL, used_at INTEGER CHECK(used_at IS NULL OR (typeof(used_at)='integer' AND used_at BETWEEN 0 AND 253402300799999)), revoked_at INTEGER CHECK(revoked_at IS NULL OR (typeof(revoked_at)='integer' AND revoked_at BETWEEN 0 AND 253402300799999)),
 delivery_state TEXT NOT NULL CHECK(delivery_state IN ('PENDING','SENT','FAILED')),
 CHECK(expiry>issued_at AND expiry<=issued_at+CASE purpose WHEN 'RESET' THEN 900000 ELSE 86400000 END));

INSERT INTO ms_account_tokens (id,user_id,purpose,secret_hash,security_version,issued_at,expiry,used_at,revoked_at,delivery_state) SELECT id,user_id,purpose,secret_hash,security_version,school_seconds_to_ms(issued_at),school_seconds_to_ms(expiry),school_seconds_to_ms(used_at),school_seconds_to_ms(revoked_at),delivery_state FROM account_tokens;

CREATE TABLE ms_auth_rate_limits (
 key_hash TEXT CHECK(length(key_hash)=64 AND key_hash NOT GLOB '*[^0-9a-f]*') PRIMARY KEY, purpose TEXT NOT NULL, window_start INTEGER CHECK(window_start IS NULL OR (typeof(window_start)='integer' AND window_start BETWEEN 0 AND 253402300799999)) NOT NULL,
 attempts INTEGER NOT NULL CHECK(attempts>=0), blocked_until INTEGER CHECK(blocked_until IS NULL OR (typeof(blocked_until)='integer' AND blocked_until BETWEEN 0 AND 253402300799999)), expires_at INTEGER CHECK(expires_at IS NULL OR (typeof(expires_at)='integer' AND expires_at BETWEEN 0 AND 253402300799999)) NOT NULL);

INSERT INTO ms_auth_rate_limits (key_hash,purpose,window_start,attempts,blocked_until,expires_at) SELECT key_hash,purpose,school_seconds_to_ms(window_start),attempts,school_seconds_to_ms(blocked_until),school_seconds_to_ms(expires_at) FROM auth_rate_limits;

CREATE TABLE ms_devices (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), owner_id TEXT NOT NULL REFERENCES ms_users(id), client_device_id TEXT NOT NULL,
 label TEXT NOT NULL CHECK(length(label) BETWEEN 1 AND 80), status TEXT NOT NULL CHECK(status IN ('ACTIVE','REVOKED')),
 token_hash TEXT CHECK(length(token_hash)=64 AND token_hash NOT GLOB '*[^0-9a-f]*') UNIQUE, parent_session_id TEXT NOT NULL REFERENCES ms_browser_sessions(id),
 boot_id TEXT NOT NULL, security_version INTEGER NOT NULL CHECK(security_version>=1),
 expiry INTEGER CHECK(expiry IS NULL OR (typeof(expiry)='integer' AND expiry BETWEEN 0 AND 253402300799999)) NOT NULL, revoked_at INTEGER CHECK(revoked_at IS NULL OR (typeof(revoked_at)='integer' AND revoked_at BETWEEN 0 AND 253402300799999)), last_seen_at INTEGER CHECK(last_seen_at IS NULL OR (typeof(last_seen_at)='integer' AND last_seen_at BETWEEN 0 AND 253402300799999)), UNIQUE(owner_id,client_device_id));

INSERT INTO ms_devices (id,owner_id,client_device_id,label,status,token_hash,parent_session_id,boot_id,security_version,expiry,revoked_at,last_seen_at) SELECT id,owner_id,client_device_id,label,status,token_hash,parent_session_id,boot_id,security_version,school_seconds_to_ms(expiry),school_seconds_to_ms(revoked_at),school_seconds_to_ms(last_seen_at) FROM devices;

CREATE TABLE ms_pairing_challenges (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), code_hmac TEXT CHECK(length(code_hmac)=64 AND code_hmac NOT GLOB '*[^0-9a-f]*') NOT NULL, owner_id TEXT NOT NULL REFERENCES ms_users(id),
 parent_session_id TEXT NOT NULL REFERENCES ms_browser_sessions(id), boot_id TEXT NOT NULL, label TEXT NOT NULL,
 issued_at INTEGER CHECK(issued_at IS NULL OR (typeof(issued_at)='integer' AND issued_at BETWEEN 0 AND 253402300799999)) NOT NULL, expiry INTEGER CHECK(expiry IS NULL OR (typeof(expiry)='integer' AND expiry BETWEEN 0 AND 253402300799999)) NOT NULL CHECK(expiry>issued_at AND expiry<=issued_at+300000),
 attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts BETWEEN 0 AND 5), used_at INTEGER CHECK(used_at IS NULL OR (typeof(used_at)='integer' AND used_at BETWEEN 0 AND 253402300799999)), revoked_at INTEGER CHECK(revoked_at IS NULL OR (typeof(revoked_at)='integer' AND revoked_at BETWEEN 0 AND 253402300799999)));

INSERT INTO ms_pairing_challenges (id,code_hmac,owner_id,parent_session_id,boot_id,label,issued_at,expiry,attempts,used_at,revoked_at) SELECT id,code_hmac,owner_id,parent_session_id,boot_id,label,school_seconds_to_ms(issued_at),school_seconds_to_ms(expiry),attempts,school_seconds_to_ms(used_at),school_seconds_to_ms(revoked_at) FROM pairing_challenges;

CREATE TABLE ms_config_versions (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), kind TEXT NOT NULL CHECK(kind IN ('ROUTE','SIGNAL','MODEL')), logical_id TEXT NOT NULL,
 version INTEGER NOT NULL CHECK(version>=1), payload TEXT NOT NULL CHECK(json_valid(payload)), payload_hash TEXT CHECK(length(payload_hash)=64 AND payload_hash NOT GLOB '*[^0-9a-f]*') NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('DRAFT','PUBLISHED','ARCHIVED')), creator_id TEXT NOT NULL REFERENCES ms_users(id),
 created_at INTEGER CHECK(created_at IS NULL OR (typeof(created_at)='integer' AND created_at BETWEEN 0 AND 253402300799999)) NOT NULL, published_at INTEGER CHECK(published_at IS NULL OR (typeof(published_at)='integer' AND published_at BETWEEN 0 AND 253402300799999)), revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1),
 UNIQUE(kind,logical_id,version));

INSERT INTO ms_config_versions (id,kind,logical_id,version,payload,payload_hash,status,creator_id,created_at,published_at,revision) SELECT id,kind,logical_id,version,payload,payload_hash,status,creator_id,school_seconds_to_ms(created_at),school_seconds_to_ms(published_at),revision FROM config_versions;

CREATE TABLE ms_trips (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), owner_id TEXT NOT NULL REFERENCES ms_users(id), title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 120),
 note TEXT NOT NULL DEFAULT '' CHECK(length(note)<=1000), mode TEXT NOT NULL CHECK(mode IN ('SIMULATION','LIVE')),
 route_version_id TEXT REFERENCES ms_config_versions(id),
 status TEXT NOT NULL CHECK(status IN ('PLANNED','STARTING','RECORDING','FINALIZING','COMPLETE','INTERRUPTED')),
 created_at INTEGER CHECK(created_at IS NULL OR (typeof(created_at)='integer' AND created_at BETWEEN 0 AND 253402300799999)) NOT NULL, started_at INTEGER CHECK(started_at IS NULL OR (typeof(started_at)='integer' AND started_at BETWEEN 0 AND 253402300799999)), ended_at INTEGER CHECK(ended_at IS NULL OR (typeof(ended_at)='integer' AND ended_at BETWEEN 0 AND 253402300799999)), run_id TEXT, raw_ref TEXT, raw_hash TEXT, manifest_hash TEXT,
 revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1), archived_at INTEGER CHECK(archived_at IS NULL OR (typeof(archived_at)='integer' AND archived_at BETWEEN 0 AND 253402300799999)),
 CHECK(ended_at IS NULL OR (started_at IS NOT NULL AND ended_at>=started_at)),
 CHECK(status!='COMPLETE' OR (started_at IS NOT NULL AND ended_at IS NOT NULL AND run_id IS NOT NULL AND raw_ref IS NOT NULL AND length(raw_hash)=64 AND length(manifest_hash)=64)),
 CHECK(archived_at IS NULL OR status IN ('PLANNED','COMPLETE','INTERRUPTED')));

INSERT INTO ms_trips (id,owner_id,title,note,mode,route_version_id,status,created_at,started_at,ended_at,run_id,raw_ref,raw_hash,manifest_hash,revision,archived_at) SELECT id,owner_id,title,note,mode,route_version_id,status,school_seconds_to_ms(created_at),school_seconds_to_ms(started_at),school_seconds_to_ms(ended_at),run_id,raw_ref,raw_hash,manifest_hash,revision,school_seconds_to_ms(archived_at) FROM trips;

CREATE TABLE ms_observations (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), trip_id TEXT NOT NULL REFERENCES ms_trips(id), actor_id TEXT NOT NULL REFERENCES ms_users(id), signal_id TEXT NOT NULL,
 source TEXT NOT NULL CHECK(source IN ('MANUAL','CV')), state TEXT NOT NULL CHECK(state IN ('RED','YELLOW','GREEN','RED_YELLOW','OFF','UNKNOWN')),
 event_type TEXT NOT NULL CHECK(event_type IN ('STATE_SEEN','STATE_START')),
 server_received_at INTEGER CHECK(server_received_at IS NULL OR (typeof(server_received_at)='integer' AND server_received_at BETWEEN 0 AND 253402300799999)) NOT NULL, measured_at INTEGER CHECK(measured_at IS NULL OR (typeof(measured_at)='integer' AND measured_at BETWEEN 0 AND 253402300799999)), geometry_hash TEXT, raw_sequence INTEGER CHECK(raw_sequence>=0),
 source_event_id TEXT NOT NULL, journaling_state TEXT NOT NULL DEFAULT 'PENDING' CHECK(journaling_state IN ('PENDING','APPLIED','FAILED')),
 CHECK(state!='UNKNOWN' OR event_type!='STATE_START'), UNIQUE(trip_id,source,source_event_id));

INSERT INTO ms_observations (id,trip_id,actor_id,signal_id,source,state,event_type,server_received_at,measured_at,geometry_hash,raw_sequence,source_event_id,journaling_state) SELECT id,trip_id,actor_id,signal_id,source,state,event_type,school_seconds_to_ms(server_received_at),school_seconds_to_ms(measured_at),geometry_hash,raw_sequence,source_event_id,journaling_state FROM observations;

CREATE TABLE ms_observation_corrections (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), observation_id TEXT NOT NULL REFERENCES ms_observations(id), actor_id TEXT NOT NULL REFERENCES ms_users(id),
 sequence INTEGER NOT NULL CHECK(sequence>=1), previous_revision INTEGER NOT NULL CHECK(previous_revision>=0),
 before_json TEXT NOT NULL CHECK(json_valid(before_json)), after_json TEXT NOT NULL CHECK(json_valid(after_json)),
 reason TEXT NOT NULL CHECK(length(reason) BETWEEN 3 AND 500), server_at INTEGER CHECK(server_at IS NULL OR (typeof(server_at)='integer' AND server_at BETWEEN 0 AND 253402300799999)) NOT NULL,
 client_operation_id TEXT NOT NULL, request_hash TEXT CHECK(length(request_hash)=64 AND request_hash NOT GLOB '*[^0-9a-f]*') NOT NULL,
 CHECK(sequence=previous_revision+1), UNIQUE(observation_id,sequence), UNIQUE(actor_id,client_operation_id));

INSERT INTO ms_observation_corrections (id,observation_id,actor_id,sequence,previous_revision,before_json,after_json,reason,server_at,client_operation_id,request_hash) SELECT id,observation_id,actor_id,sequence,previous_revision,before_json,after_json,reason,school_seconds_to_ms(server_at),client_operation_id,request_hash FROM observation_corrections;

CREATE TABLE ms_trip_shares (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), trip_id TEXT NOT NULL REFERENCES ms_trips(id), analyst_id TEXT NOT NULL REFERENCES ms_users(id),
 grantor_id TEXT NOT NULL REFERENCES ms_users(id), permission TEXT NOT NULL DEFAULT 'READ_ANALYZE' CHECK(permission='READ_ANALYZE'),
 created_at INTEGER CHECK(created_at IS NULL OR (typeof(created_at)='integer' AND created_at BETWEEN 0 AND 253402300799999)) NOT NULL, revoked_at INTEGER CHECK(revoked_at IS NULL OR (typeof(revoked_at)='integer' AND revoked_at BETWEEN 0 AND 253402300799999)));

INSERT INTO ms_trip_shares (id,trip_id,analyst_id,grantor_id,permission,created_at,revoked_at) SELECT id,trip_id,analyst_id,grantor_id,permission,school_seconds_to_ms(created_at),school_seconds_to_ms(revoked_at) FROM trip_shares;

CREATE TABLE ms_audit_events (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, actor_id TEXT REFERENCES ms_users(id), actor_type TEXT NOT NULL,
 action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '',
 server_at INTEGER CHECK(server_at IS NULL OR (typeof(server_at)='integer' AND server_at BETWEEN 0 AND 253402300799999)) NOT NULL, request_id TEXT NOT NULL, outcome TEXT NOT NULL);

INSERT INTO ms_audit_events (sequence,actor_id,actor_type,action,resource_type,resource_id,reason,server_at,request_id,outcome) SELECT sequence,actor_id,actor_type,action,resource_type,resource_id,reason,school_seconds_to_ms(server_at),request_id,outcome FROM audit_events;

CREATE TABLE ms_recording_operations (
 id TEXT PRIMARY KEY CHECK(length(id)=32 AND id NOT GLOB '*[^0-9a-f]*'), trip_id TEXT NOT NULL REFERENCES ms_trips(id), actor_id TEXT NOT NULL REFERENCES ms_users(id),
 kind TEXT NOT NULL CHECK(kind IN ('START','FINISH','JOURNAL_OBSERVATION')),
 idempotency_key TEXT NOT NULL CHECK(length(idempotency_key) BETWEEN 32 AND 64), request_hash TEXT CHECK(length(request_hash)=64 AND request_hash NOT GLOB '*[^0-9a-f]*') NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('PENDING','APPLIED','FAILED')), result_ref TEXT, created_at INTEGER CHECK(created_at IS NULL OR (typeof(created_at)='integer' AND created_at BETWEEN 0 AND 253402300799999)) NOT NULL,
 UNIQUE(actor_id,kind,idempotency_key));

INSERT INTO ms_recording_operations (id,trip_id,actor_id,kind,idempotency_key,request_hash,state,result_ref,created_at) SELECT id,trip_id,actor_id,kind,idempotency_key,request_hash,state,result_ref,school_seconds_to_ms(created_at) FROM recording_operations;

UPDATE sqlite_sequence SET seq=max(seq,COALESCE((SELECT seq FROM sqlite_sequence WHERE name='audit_events'),0)) WHERE name='ms_audit_events';

DROP TABLE recording_operations;

DROP TABLE audit_events;

DROP TABLE trip_shares;

DROP TABLE observation_corrections;

DROP TABLE observations;

DROP TABLE trips;

DROP TABLE config_versions;

DROP TABLE pairing_challenges;

DROP TABLE devices;

DROP TABLE auth_rate_limits;

DROP TABLE account_tokens;

DROP TABLE browser_sessions;

DROP TABLE users;

DROP TABLE schema_migrations;

ALTER TABLE ms_schema_migrations RENAME TO schema_migrations;

ALTER TABLE ms_users RENAME TO users;

ALTER TABLE ms_browser_sessions RENAME TO browser_sessions;

ALTER TABLE ms_account_tokens RENAME TO account_tokens;

ALTER TABLE ms_auth_rate_limits RENAME TO auth_rate_limits;

ALTER TABLE ms_devices RENAME TO devices;

ALTER TABLE ms_pairing_challenges RENAME TO pairing_challenges;

ALTER TABLE ms_config_versions RENAME TO config_versions;

ALTER TABLE ms_trips RENAME TO trips;

ALTER TABLE ms_observations RENAME TO observations;

ALTER TABLE ms_observation_corrections RENAME TO observation_corrections;

ALTER TABLE ms_trip_shares RENAME TO trip_shares;

ALTER TABLE ms_audit_events RENAME TO audit_events;

ALTER TABLE ms_recording_operations RENAME TO recording_operations;

CREATE INDEX sessions_owner ON browser_sessions(user_id,revoked_at);

CREATE INDEX sessions_expiry ON browser_sessions(absolute_expiry);

CREATE UNIQUE INDEX tokens_active ON account_tokens(user_id,purpose) WHERE used_at IS NULL AND revoked_at IS NULL;

CREATE INDEX tokens_expiry ON account_tokens(user_id,purpose,expiry);

CREATE UNIQUE INDEX pair_code ON pairing_challenges(code_hmac) WHERE used_at IS NULL AND revoked_at IS NULL;

CREATE UNIQUE INDEX pair_parent ON pairing_challenges(parent_session_id) WHERE used_at IS NULL AND revoked_at IS NULL;

CREATE INDEX trips_owner_date ON trips(owner_id,created_at,id);

CREATE INDEX trips_owner_filter ON trips(owner_id,route_version_id,status,created_at);

CREATE INDEX observations_date ON observations(trip_id,server_received_at,id);

CREATE INDEX observations_filter ON observations(trip_id,signal_id,state,event_type,server_received_at);

CREATE UNIQUE INDEX shares_active ON trip_shares(trip_id) WHERE revoked_at IS NULL;

CREATE INDEX shares_recipient ON trip_shares(analyst_id,revoked_at,trip_id);

CREATE INDEX audit_actor_date ON audit_events(actor_id,server_at);

CREATE INDEX audit_resource_date ON audit_events(resource_type,resource_id,server_at);

CREATE TRIGGER observation_facts BEFORE UPDATE ON observations WHEN
 NEW.id IS NOT OLD.id OR NEW.trip_id IS NOT OLD.trip_id OR NEW.actor_id IS NOT OLD.actor_id OR NEW.signal_id IS NOT OLD.signal_id OR
 NEW.source IS NOT OLD.source OR NEW.state IS NOT OLD.state OR NEW.event_type IS NOT OLD.event_type OR
 NEW.server_received_at IS NOT OLD.server_received_at OR NEW.measured_at IS NOT OLD.measured_at OR
 NEW.geometry_hash IS NOT OLD.geometry_hash OR NEW.source_event_id IS NOT OLD.source_event_id
 BEGIN SELECT RAISE(ABORT,'immutable observation facts'); END;

CREATE TRIGGER observation_no_delete BEFORE DELETE ON observations BEGIN SELECT RAISE(ABORT,'immutable observation'); END;

CREATE TRIGGER correction_no_update BEFORE UPDATE ON observation_corrections BEGIN SELECT RAISE(ABORT,'immutable correction'); END;

CREATE TRIGGER correction_no_delete BEFORE DELETE ON observation_corrections BEGIN SELECT RAISE(ABORT,'immutable correction'); END;

CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT,'append-only audit'); END;

CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT,'append-only audit'); END;

CREATE TRIGGER trip_identity BEFORE UPDATE ON trips WHEN NEW.owner_id IS NOT OLD.owner_id OR NEW.id IS NOT OLD.id OR
 (OLD.started_at IS NOT NULL AND (NEW.mode IS NOT OLD.mode OR NEW.route_version_id IS NOT OLD.route_version_id OR NEW.run_id IS NOT OLD.run_id OR NEW.started_at IS NOT OLD.started_at OR NEW.created_at IS NOT OLD.created_at))
 BEGIN SELECT RAISE(ABORT,'immutable trip identity'); END;

CREATE TRIGGER published_config BEFORE UPDATE ON config_versions WHEN OLD.status!='DRAFT' AND
 (NEW.payload IS NOT OLD.payload OR NEW.payload_hash IS NOT OLD.payload_hash OR NEW.kind IS NOT OLD.kind OR NEW.logical_id IS NOT OLD.logical_id OR NEW.version IS NOT OLD.version OR NEW.creator_id IS NOT OLD.creator_id)
 BEGIN SELECT RAISE(ABORT,'immutable published configuration'); END;

CREATE TRIGGER device_parent_insert BEFORE INSERT ON devices WHEN NOT EXISTS
 (SELECT 1 FROM browser_sessions WHERE id=NEW.parent_session_id AND user_id=NEW.owner_id)
 BEGIN SELECT RAISE(ABORT,'device session owner mismatch'); END;

CREATE TRIGGER device_parent_update BEFORE UPDATE ON devices WHEN NEW.owner_id IS NOT OLD.owner_id OR NOT EXISTS
 (SELECT 1 FROM browser_sessions WHERE id=NEW.parent_session_id AND user_id=NEW.owner_id)
 BEGIN SELECT RAISE(ABORT,'device session owner mismatch'); END;

CREATE TRIGGER pairing_parent BEFORE INSERT ON pairing_challenges WHEN NOT EXISTS
 (SELECT 1 FROM browser_sessions WHERE id=NEW.parent_session_id AND user_id=NEW.owner_id)
 BEGIN SELECT RAISE(ABORT,'pairing session owner mismatch'); END;

CREATE TRIGGER observation_owner BEFORE INSERT ON observations WHEN NOT EXISTS
 (SELECT 1 FROM trips WHERE id=NEW.trip_id AND owner_id=NEW.actor_id)
 BEGIN SELECT RAISE(ABORT,'observation owner mismatch'); END;

CREATE TRIGGER correction_owner BEFORE INSERT ON observation_corrections WHEN NOT EXISTS
 (SELECT 1 FROM observations o JOIN trips t ON t.id=o.trip_id WHERE o.id=NEW.observation_id AND t.owner_id=NEW.actor_id AND t.archived_at IS NULL)
 OR NEW.previous_revision != (SELECT COALESCE(max(sequence),0) FROM observation_corrections WHERE observation_id=NEW.observation_id)
 BEGIN SELECT RAISE(ABORT,'correction owner or revision mismatch'); END;

CREATE TRIGGER share_eligible BEFORE INSERT ON trip_shares WHEN NOT EXISTS
 (SELECT 1 FROM trips t JOIN users u ON u.id=NEW.analyst_id WHERE t.id=NEW.trip_id AND t.owner_id=NEW.grantor_id AND t.status='COMPLETE' AND t.archived_at IS NULL AND u.role='ANALYST' AND u.status='ACTIVE' AND u.id!=t.owner_id)
 BEGIN SELECT RAISE(ABORT,'share not eligible'); END;

CREATE TRIGGER share_identity BEFORE UPDATE ON trip_shares WHEN NEW.id IS NOT OLD.id OR NEW.trip_id IS NOT OLD.trip_id OR
 NEW.analyst_id IS NOT OLD.analyst_id OR NEW.grantor_id IS NOT OLD.grantor_id OR NEW.permission IS NOT OLD.permission OR
 NEW.created_at IS NOT OLD.created_at OR (OLD.revoked_at IS NOT NULL AND NEW.revoked_at IS NOT OLD.revoked_at)
 BEGIN SELECT RAISE(ABORT,'immutable share grant'); END;

CREATE TRIGGER finished_trip BEFORE UPDATE ON trips WHEN OLD.status IN ('COMPLETE','INTERRUPTED') AND
 (NEW.status IS NOT OLD.status OR NEW.ended_at IS NOT OLD.ended_at OR NEW.raw_ref IS NOT OLD.raw_ref OR NEW.raw_hash IS NOT OLD.raw_hash OR NEW.manifest_hash IS NOT OLD.manifest_hash)
 BEGIN SELECT RAISE(ABORT,'immutable closed trip facts'); END;

CREATE TRIGGER operation_owner BEFORE INSERT ON recording_operations WHEN NOT EXISTS
 (SELECT 1 FROM trips WHERE id=NEW.trip_id AND owner_id=NEW.actor_id)
 BEGIN SELECT RAISE(ABORT,'operation owner mismatch'); END;

CREATE TRIGGER operation_identity BEFORE UPDATE ON recording_operations WHEN NEW.id IS NOT OLD.id OR NEW.trip_id IS NOT OLD.trip_id OR
 NEW.actor_id IS NOT OLD.actor_id OR NEW.kind IS NOT OLD.kind OR NEW.idempotency_key IS NOT OLD.idempotency_key OR
 NEW.request_hash IS NOT OLD.request_hash OR NEW.created_at IS NOT OLD.created_at OR
 (OLD.state!='PENDING' AND (NEW.state IS NOT OLD.state OR NEW.result_ref IS NOT OLD.result_ref))
 BEGIN SELECT RAISE(ABORT,'immutable recording intent'); END;
