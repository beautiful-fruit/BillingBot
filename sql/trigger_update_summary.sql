CREATE OR REPLACE FUNCTION update_summary_on_insert()
RETURNS TRIGGER AS $$
DECLARE
    v_user1 BIGINT;
    v_user2 BIGINT;
    v_amount INTEGER;
BEGIN
    IF NEW.amount IS NOT NULL AND NEW.pending = FALSE THEN
        SELECT o_user1, o_user2, o_amount
        INTO v_user1, v_user2, v_amount
        FROM sort_borrow_or_return_users(
            NEW.from_uid,
            NEW.to_uid,
            NEW.amount,
            FALSE
        );
                    
        PERFORM update_summary_amount(v_user1, v_user2, v_amount);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_summary_on_delete()
RETURNS TRIGGER AS $$
DECLARE
    v_user1 BIGINT;
    v_user2 BIGINT;
    v_amount INTEGER;
BEGIN
    IF OLD.amount IS NOT NULL AND OLD.pending = FALSE AND OLD.amount > 0 THEN
        SELECT o_user1, o_user2, o_amount
        INTO v_user1, v_user2, v_amount
        FROM sort_borrow_or_return_users(
            OLD.from_uid,
            OLD.to_uid,
            OLD.amount,
            TRUE
        );
                    
        PERFORM update_summary_amount(v_user1, v_user2, v_amount);
    END IF;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_summary_on_update()
RETURNS TRIGGER AS $$
DECLARE
    v_user1 BIGINT;
    v_user2 BIGINT;
    v_amount INTEGER;
BEGIN
    IF OLD.amount IS NOT NULL AND OLD.pending = FALSE THEN
        SELECT o_user1, o_user2, o_amount
        INTO v_user1, v_user2, v_amount
        FROM sort_borrow_or_return_users(
            OLD.from_uid,
            OLD.to_uid,
            OLD.amount,
            TRUE
        );
        PERFORM update_summary_amount(v_user1, v_user2, v_amount);
    END IF;
                    
    IF NEW.amount IS NOT NULL AND NEW.pending = FALSE THEN
        SELECT o_user1, o_user2, o_amount
        INTO v_user1, v_user2, v_amount
        FROM sort_borrow_or_return_users(
            NEW.from_uid,
            NEW.to_uid,
            NEW.amount,
            FALSE
        );
        PERFORM update_summary_amount(v_user1, v_user2, v_amount);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_summary_amount(
    p_user1 BIGINT,
    p_user2 BIGINT,
    p_amount INTEGER
)
RETURNS VOID AS $$
DECLARE
    v_current_amount INTEGER;
BEGIN
    SELECT amount INTO v_current_amount FROM summary
    WHERE user1 = p_user1 AND user2 = p_user2;
    
    IF FOUND THEN
        v_current_amount := v_current_amount + p_amount;
        UPDATE summary SET amount = v_current_amount
        WHERE user1 = p_user1 AND user2 = p_user2;
    ELSE
        INSERT INTO summary (user1, user2, amount)
        VALUES (p_user1, p_user2, p_amount);
    END IF;
END;
$$ LANGUAGE plpgsql;
                    
CREATE OR REPLACE FUNCTION sort_borrow_or_return_users(
    p_user_a BIGINT,
    p_user_b BIGINT,
    p_amount INTEGER,
    p_reverse BOOLEAN,
    OUT o_user1 BIGINT,
    OUT o_user2 BIGINT,
    OUT o_amount INTEGER
) AS $$
BEGIN
    IF p_user_a < p_user_b THEN
        o_user1 := p_user_a;
        o_user2 := p_user_b;
        o_amount := CASE WHEN p_reverse THEN -p_amount ELSE p_amount END;
    ELSE
        o_user1 := p_user_b;
        o_user2 := p_user_a;
        o_amount := CASE WHEN p_reverse THEN p_amount ELSE -p_amount END;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_borrow_update_summary_on_insert
AFTER INSERT ON borrow_history
FOR EACH ROW
EXECUTE FUNCTION update_summary_on_insert();
    
CREATE OR REPLACE TRIGGER trg_borrow_update_summary_on_update
AFTER UPDATE ON borrow_history
FOR EACH ROW
EXECUTE FUNCTION update_summary_on_update();
    
CREATE OR REPLACE TRIGGER trg_borrow_revert_summary_on_delete
AFTER DELETE ON borrow_history
FOR EACH ROW
EXECUTE FUNCTION update_summary_on_delete();

CREATE OR REPLACE TRIGGER trg_return_update_summary_on_insert
AFTER INSERT ON return_history
FOR EACH ROW
EXECUTE FUNCTION update_summary_on_insert();
    
CREATE OR REPLACE TRIGGER trg_return_update_summary_on_update
AFTER UPDATE ON return_history
FOR EACH ROW
EXECUTE FUNCTION update_summary_on_update();
    
CREATE OR REPLACE TRIGGER trg_return_revert_summary_on_delete
AFTER DELETE ON return_history
FOR EACH ROW
EXECUTE FUNCTION update_summary_on_delete();
