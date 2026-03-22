-- Optional schema cleanup for mixed AI/manual article creation.
-- The current backend code already supports manual article creation without this,
-- by normalizing missing keyword/run_id before insert.
-- Apply this migration if you want the database schema itself to reflect that model.

ALTER TABLE blog_posts
    ALTER COLUMN keyword DROP NOT NULL,
    ALTER COLUMN run_id DROP NOT NULL;

ALTER TABLE blog_posts
    ADD COLUMN IF NOT EXISTS content_source VARCHAR(16) NOT NULL DEFAULT 'ai';

UPDATE blog_posts
SET content_source = 'manual'
WHERE run_id LIKE 'manual-%';
