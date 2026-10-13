ALTER TABLE observations ADD COLUMN historical INTEGER NOT NULL DEFAULT 0;
ALTER TABLE recording_operations ADD COLUMN parent_session_id TEXT REFERENCES browser_sessions(id);
ALTER TABLE recording_operations ADD COLUMN boot_id TEXT;
ALTER TABLE recording_operations ADD COLUMN observation_id TEXT REFERENCES observations(id);
CREATE INDEX operations_trip_state ON recording_operations(trip_id,state,kind);
CREATE INDEX observations_global_date ON observations(server_received_at,id);
DROP TRIGGER observation_facts;
CREATE TRIGGER observation_facts BEFORE UPDATE ON observations WHEN
 NEW.historical IS NOT OLD.historical OR NEW.id IS NOT OLD.id OR NEW.trip_id IS NOT OLD.trip_id OR NEW.actor_id IS NOT OLD.actor_id OR NEW.signal_id IS NOT OLD.signal_id OR
 NEW.source IS NOT OLD.source OR NEW.state IS NOT OLD.state OR NEW.event_type IS NOT OLD.event_type OR
 NEW.server_received_at IS NOT OLD.server_received_at OR NEW.measured_at IS NOT OLD.measured_at OR
 NEW.geometry_hash IS NOT OLD.geometry_hash OR NEW.source_event_id IS NOT OLD.source_event_id
 BEGIN SELECT RAISE(ABORT,'immutable observation facts'); END;
CREATE TRIGGER operation_context_immutable BEFORE UPDATE ON recording_operations WHEN
NEW.parent_session_id IS NOT OLD.parent_session_id OR NEW.boot_id IS NOT OLD.boot_id OR NEW.observation_id IS NOT OLD.observation_id
BEGIN SELECT RAISE(ABORT,'immutable operation context'); END;
CREATE TRIGGER operation_context_parent BEFORE INSERT ON recording_operations WHEN
(NEW.parent_session_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM browser_sessions WHERE id=NEW.parent_session_id AND user_id=NEW.actor_id)) OR
(NEW.observation_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM observations WHERE id=NEW.observation_id AND trip_id=NEW.trip_id AND actor_id=NEW.actor_id))
BEGIN SELECT RAISE(ABORT,'operation context mismatch'); END;
CREATE TRIGGER observation_history_valid BEFORE INSERT ON observations WHEN
TYPEOF(NEW.historical)!='integer' OR NEW.historical NOT IN (0,1) OR (NEW.historical=1 AND NEW.measured_at IS NOT NULL)
BEGIN SELECT RAISE(ABORT,'invalid historical observation'); END;
