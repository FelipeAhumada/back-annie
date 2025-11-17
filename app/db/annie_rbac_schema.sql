-- ============================================================================
-- Annie-AI RBAC Schema Migration
-- ============================================================================
-- This migration updates the roles table to use the correct role names:
-- owner, admin, agent, observer (instead of admin, manager, agent, viewer)
--
-- Run this migration after the base schema (annie_auth_schema.sql)
-- ============================================================================

BEGIN;

-- Update roles to match RBAC requirements: owner, admin, agent, observer
-- First, delete old roles if they exist
DELETE FROM roles WHERE name IN ('manager', 'viewer');

-- Insert/update roles with correct names and hierarchy
INSERT INTO roles (id, name, describe) VALUES
  (1, 'owner',    'Full access: can delete organization, manage billing, and all admin functions'),
  (2, 'admin',    'Administrative access: can manage members, channels, campaigns, and all CRM functions'),
  (3, 'agent',    'Agent access: can manage leads, respond to conversations, and view analytics'),
  (4, 'observer', 'Read-only access: can view leads, conversations, and analytics but cannot make changes')
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    describe = EXCLUDED.describe;

-- Ensure role names are unique
CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

-- Add index for faster role lookups
CREATE INDEX IF NOT EXISTS idx_user_tenants_user ON user_tenants(user_id);
CREATE INDEX IF NOT EXISTS idx_user_tenants_role ON user_tenants(role_id);

-- Add comment to user_tenants table for documentation
COMMENT ON TABLE user_tenants IS 'Multi-tenant RBAC: Links users to tenants with specific roles (owner, admin, agent, observer)';
COMMENT ON COLUMN user_tenants.role_id IS 'References roles.id - determines user permissions within the tenant';

COMMIT;

