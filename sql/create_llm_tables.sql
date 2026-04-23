CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    user_id BIGINT,
    username TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    message_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id 
    ON chat_messages (user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_channel_id
    ON chat_messages (channel_id);


CREATE TABLE IF NOT EXISTS timers (
    id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    trigger_time TIMESTAMPTZ NOT NULL,
    message TEXT NOT NULL,
    original_message TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_timers_user_id 
    ON timers (user_id);
CREATE INDEX IF NOT EXISTS idx_timers_channel_id 
    ON timers (channel_id);
