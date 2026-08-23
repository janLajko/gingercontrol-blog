-- 新增 purchase_type='one_time_ginger'：非 Stripe 渠道产生的一次性购买
-- （例如管理员手动发放、邀请码赠送），与真实走 Stripe 的 'one_time' 区分开。
ALTER TABLE billing_purchase
    DROP CONSTRAINT IF EXISTS ck_billing_purchase_type;

ALTER TABLE billing_purchase
    ADD CONSTRAINT ck_billing_purchase_type
        CHECK (purchase_type IN ('subscription', 'one_time', 'one_time_ginger'));
