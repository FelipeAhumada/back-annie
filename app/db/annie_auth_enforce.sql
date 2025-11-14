BEGIN;

-- 1) Asegurar que TODO usuario tenga al menos un tenant asociado al COMMIT
CREATE OR REPLACE FUNCTION ensure_user_has_tenant()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  PERFORM 1 FROM user_tenants WHERE user_id = COALESCE(NEW.id, OLD.id) LIMIT 1;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'User % must be associated to at least one tenant', COALESCE(NEW.id, OLD.id)
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_users_must_have_tenant ON users;
CREATE CONSTRAINT TRIGGER trg_users_must_have_tenant
AFTER INSERT OR UPDATE ON users
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION ensure_user_has_tenant();

-- 2) Prevenir borrar la ÚLTIMA relación user_tenants (a menos que se borre el user completo)
CREATE OR REPLACE FUNCTION prevent_removing_last_user_tenant()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  cnt int;
BEGIN
  SELECT COUNT(*) INTO cnt FROM user_tenants WHERE user_id = OLD.user_id;
  IF cnt <= 1 THEN
    RAISE EXCEPTION 'Cannot remove last tenant relation for user %', OLD.user_id
      USING ERRCODE = '23503';
  END IF;
  RETURN OLD;
END $$;

DROP TRIGGER IF EXISTS trg_prevent_last_relation ON user_tenants;
CREATE TRIGGER trg_prevent_last_relation
BEFORE DELETE ON user_tenants
FOR EACH ROW
EXECUTE FUNCTION prevent_removing_last_user_tenant();

COMMIT;
