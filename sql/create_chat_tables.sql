DROP TABLE IF EXISTS chat_messages CASCADE;

CREATE TABLE chat_messages (
    id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    user_id BIGINT,
    username TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_id BIGINT
);

CREATE INDEX idx_chat_messages_channel_id_created_at 
    ON chat_messages (channel_id, created_at);
CREATE INDEX idx_chat_messages_user_id 
    ON chat_messages (user_id);