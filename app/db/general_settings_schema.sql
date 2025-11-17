-- ============================================================================
-- General Settings Schema Migration
-- ============================================================================
-- Creates the general_settings table for tenant-specific organization information
-- One record per tenant (enforced by unique constraint on tenant_id)
-- ============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS general_settings (
    tenant_id          TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    logo_url           TEXT,
    website_url        TEXT,
    short_description  TEXT,
    mission            TEXT,
    vision             TEXT,
    purpose            TEXT,
    customer_problems  TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_general_settings_tenant ON general_settings(tenant_id);

-- Add comment for documentation
COMMENT ON TABLE general_settings IS 'General organization settings per tenant (name, description, mission, vision, etc.)';
COMMENT ON COLUMN general_settings.tenant_id IS 'Foreign key to tenants table - one record per tenant';

COMMIT;

