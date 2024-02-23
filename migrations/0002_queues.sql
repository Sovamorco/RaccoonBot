CREATE TABLE queues (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    message_id BIGINT,
    page INT
);