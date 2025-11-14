BEGIN;

-- Usuarios del sistema (multi-tenant por relación en user_tenants)
CREATE TABLE IF NOT EXISTS users (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email           TEXT NOT NULL UNIQUE,
  password_hash   TEXT NOT NULL,
  full_name       TEXT,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Roles disponibles por tenant
CREATE TABLE IF NOT EXISTS roles (
  id        SERIAL PRIMARY KEY,
  name      TEXT NOT NULL UNIQUE,         -- admin, manager, agent, viewer
  describe  TEXT
);

-- Relación usuario <-> tenant con rol
CREATE TABLE IF NOT EXISTS user_tenants (
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role_id    INT NOT NULL REFERENCES roles(id),
  PRIMARY KEY (user_id, tenant_id)
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_tenants_tenant ON user_tenants(tenant_id);

-- Semillas de roles (id fijos por simplicidad)
INSERT INTO roles (id, name, describe) VALUES
  (1, 'admin',   'Control total del tenant'),
  (2, 'manager', 'Gestión de CRM y campañas'),
  (3, 'agent',   'Atiende chat/soporte'),
  (4, 'viewer',  'Solo lectura')
ON CONFLICT (id) DO NOTHING;

COMMIT;
