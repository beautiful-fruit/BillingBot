CREATE OR REPLACE FUNCTION ensure_user_exists_common()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO users (uid)
    VALUES (NEW.from_uid), (NEW.to_uid)
    ON CONFLICT (uid) DO NOTHING;
                    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_borrow_ensure_user
BEFORE INSERT ON borrow_history
FOR EACH ROW
EXECUTE FUNCTION ensure_user_exists_common();

CREATE OR REPLACE TRIGGER trg_return_ensure_user
BEFORE INSERT ON return_history
FOR EACH ROW
EXECUTE FUNCTION ensure_user_exists_common();
