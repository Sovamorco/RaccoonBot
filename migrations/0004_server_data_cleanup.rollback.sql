ALTER TABLE server_data
ADD COLUMN volume INT DEFAULT 100 NOT NULL;
ALTER TABLE server_data
ADD COLUMN shuffle TINYINT(1) DEFAULT 0 NOT NULL;