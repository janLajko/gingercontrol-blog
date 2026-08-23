-- 新增邀请码类型 'credits'：专门用于赠送 credits 的邀请码。
ALTER TABLE invitation_codes
    DROP CONSTRAINT IF EXISTS invitation_codes_code_type_check;

ALTER TABLE invitation_codes
    ADD CONSTRAINT invitation_codes_code_type_check
        CHECK (code_type IN ('radar', 'register', 'sandbox', 'credits'));
