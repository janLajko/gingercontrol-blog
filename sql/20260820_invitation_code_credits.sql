-- 邀请码赠送 credits：兑换该邀请码的用户获得的 credits 数量。
-- NULL 表示不赠送 credits（保持既有邀请码的行为不变）。
ALTER TABLE invitation_codes
    ADD COLUMN IF NOT EXISTS credits INTEGER NULL;

ALTER TABLE invitation_codes
    DROP CONSTRAINT IF EXISTS invitation_codes_credits_check;

ALTER TABLE invitation_codes
    ADD CONSTRAINT invitation_codes_credits_check
        CHECK (credits IS NULL OR credits > 0);
