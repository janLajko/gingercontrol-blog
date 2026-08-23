-- 邀请码表
CREATE TABLE IF NOT EXISTS invitation_codes (
    id BIGSERIAL PRIMARY KEY,

    code VARCHAR(128) NOT NULL UNIQUE,
    code_type VARCHAR(32) NOT NULL,

    prefix VARCHAR(32) NOT NULL DEFAULT '',
    code_length INTEGER NOT NULL,

    max_uses INTEGER NOT NULL DEFAULT 1,
    used_count INTEGER NOT NULL DEFAULT 0,

    valid_from TIMESTAMPTZ NULL,
    valid_until TIMESTAMPTZ NULL,

    status VARCHAR(32) NOT NULL DEFAULT 'active',
    note TEXT NULL,

    -- 兑换该邀请码可获得的 credits；NULL 表示不赠送
    credits INTEGER NULL,

    created_by VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ NULL,

    CONSTRAINT invitation_codes_code_type_check
        CHECK (code_type IN ('radar', 'register', 'sandbox', 'credits')),

    CONSTRAINT invitation_codes_status_check
        CHECK (status IN ('active', 'disabled', 'expired', 'exhausted')),

    CONSTRAINT invitation_codes_code_length_check
        CHECK (code_length > 0),

    CONSTRAINT invitation_codes_max_uses_check
        CHECK (max_uses > 0),

    CONSTRAINT invitation_codes_credits_check
        CHECK (credits IS NULL OR credits > 0),

    CONSTRAINT invitation_codes_used_count_check
        CHECK (used_count >= 0 AND used_count <= max_uses),

    CONSTRAINT invitation_codes_valid_range_check
        CHECK (
            valid_from IS NULL
            OR valid_until IS NULL
            OR valid_from < valid_until
        )
);

CREATE INDEX IF NOT EXISTS idx_invitation_codes_code_type
    ON invitation_codes (code_type);

CREATE INDEX IF NOT EXISTS idx_invitation_codes_status
    ON invitation_codes (status);

CREATE INDEX IF NOT EXISTS idx_invitation_codes_valid_from
    ON invitation_codes (valid_from);

CREATE INDEX IF NOT EXISTS idx_invitation_codes_valid_until
    ON invitation_codes (valid_until);

CREATE INDEX IF NOT EXISTS idx_invitation_codes_created_at
    ON invitation_codes (created_at DESC);

-- 邀请码使用记录表：最小记录
CREATE TABLE IF NOT EXISTS invitation_code_usages (
    id BIGSERIAL PRIMARY KEY,

    code VARCHAR(128) NOT NULL REFERENCES invitation_codes(code)
        ON DELETE CASCADE,

    user_id VARCHAR(128) NOT NULL,
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitation_code_usages_code
    ON invitation_code_usages (code);

CREATE INDEX IF NOT EXISTS idx_invitation_code_usages_user_id
    ON invitation_code_usages (user_id);

CREATE INDEX IF NOT EXISTS idx_invitation_code_usages_used_at
    ON invitation_code_usages (used_at DESC);
