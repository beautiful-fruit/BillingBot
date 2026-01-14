CREATE TABLE IF NOT EXISTS users (
    uid BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS borrow_history (
    uid         BIGINT PRIMARY KEY,
    from_uid    BIGINT NOT NULL,
    to_uid      BIGINT NOT NULL,
    amount      INTEGER,
    other       TEXT,
    url         TEXT NOT NULL,
    pending     BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_borrow_from
        FOREIGN KEY (from_uid)
        REFERENCES users(uid) ON DELETE RESTRICT,
    CONSTRAINT fk_borrow_to
        FOREIGN KEY (to_uid)
        REFERENCES users(uid) ON DELETE RESTRICT,
    
    CONSTRAINT chk_borrow_amount_or_other
        CHECK (amount IS NOT NULL OR other IS NOT NULL),
    CONSTRAINT chk_borrow_positive_amount
        CHECK (amount IS NULL OR amount > 0),
    CONSTRAINT chk_borrow_not_self
        CHECK (from_uid <> to_uid)
);

CREATE TABLE IF NOT EXISTS return_history (
    uid         BIGINT PRIMARY KEY,
    from_uid    BIGINT NOT NULL,
    to_uid      BIGINT NOT NULL,
    amount      INTEGER NOT NULL,
    pending     BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT fk_return_from FOREIGN KEY (from_uid) 
        REFERENCES users(uid) ON DELETE RESTRICT,
    CONSTRAINT fk_return_to FOREIGN KEY (to_uid)
        REFERENCES users(uid) ON DELETE RESTRICT,

    CONSTRAINT chk_return_positive_return_amount
        CHECK (amount > 0),
    CONSTRAINT chk_return_not_self
        CHECK (from_uid <> to_uid)
);
                    
CREATE TABLE IF NOT EXISTS summary (
    user1   BIGINT NOT NULL,
    user2   BIGINT NOT NULL,
    amount  INTEGER NOT NULL,

    PRIMARY KEY (user1, user2),

    CONSTRAINT fk_user1 FOREIGN KEY (user1) 
        REFERENCES users(uid) ON DELETE CASCADE,
    CONSTRAINT fk_user2 FOREIGN KEY (user2) 
        REFERENCES users(uid) ON DELETE CASCADE,
    CONSTRAINT chk_user_order CHECK (user1 < user2)
);
