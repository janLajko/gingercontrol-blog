-- Add article language support.
-- Existing articles default to English.

ALTER TABLE blog_posts
    ADD COLUMN IF NOT EXISTS language VARCHAR(16) DEFAULT 'en';

CREATE INDEX IF NOT EXISTS ix_blog_posts_language
    ON blog_posts (language);

UPDATE blog_posts
SET language = 'en'
WHERE language IS NULL OR trim(language) = '';

ALTER TABLE blog_posts
    ALTER COLUMN language SET DEFAULT 'en',
    ALTER COLUMN language SET NOT NULL;
