# Flujo Completo: Admin del Tenant Demo

## ✅ Cómo Funciona el Login (Correcto)

El login **NO pide tenant_id**. El flujo es:

1. Usuario envía `email` y `password`
2. Sistema busca el usuario por email
3. Sistema obtiene **todos los tenants** del usuario desde `user_tenants`
4. Sistema devuelve token con el **primer tenant** como default
5. Sistema devuelve lista de todos los tenants disponibles

El `tenant_id` es un **atributo del usuario** (relación en `user_tenants`), no se pasa en el login.

---

## 📋 Flujo Completo para Admin Demo

### Paso 1: Crear Usuario Admin (si no existe)

**Opción A: Via API (requiere token admin/owner existente)**

```bash
# Variables
API_BASE="https://api.annie-ai.app"
ADMIN_TOKEN="<token_de_admin_o_owner_existente>"

# Crear usuario admin@demo.com
curl -X POST "$API_BASE/api/v1/admin/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "password": "Admin123",
    "full_name": "Demo Admin",
    "tenant_id": "demo-annie",
    "role": "admin"
  }'
```

**Opción B: Directo en Base de Datos (si no tienes token)**

```sql
-- 1. Crear usuario (si no existe)
INSERT INTO users (email, password_hash, full_name, is_active)
SELECT 
    'admin@demo.com',
    '$2b$12$Q3n8s3DXY0I3oA1d2k3Q8uiD9qJ1go5G3VgqgqYlI1ZJmZ5B5a8kS', -- bcrypt de "Admin123"
    'Demo Admin',
    TRUE
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@demo.com')
RETURNING id;

-- 2. Obtener IDs necesarios
WITH u AS (
    SELECT id FROM users WHERE email = 'admin@demo.com' LIMIT 1
),
r AS (
    SELECT id FROM roles WHERE name = 'admin' LIMIT 1
)
-- 3. Vincular usuario al tenant demo-annie con rol admin
INSERT INTO user_tenants (user_id, tenant_id, role_id)
SELECT u.id, 'demo-annie', r.id 
FROM u, r
ON CONFLICT (user_id, tenant_id) DO UPDATE SET role_id = EXCLUDED.role_id;
```

---

### Paso 2: Login (Solo email y password)

```bash
API_BASE="https://api.annie-ai.app"

# Login - NO se pasa tenant_id, solo email y password
RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@demo.com",
    "password": "Admin123"
  }')

# Extraer token
TOKEN=$(echo "$RESPONSE" | jq -r '.token')

# Ver respuesta completa (incluye lista de tenants)
echo "$RESPONSE" | jq '.'

# Respuesta esperada:
# {
#   "ok": true,
#   "token": "eyJ...",
#   "current_tenant": {
#     "tenant_id": "demo-annie",
#     "tenant_name": "DEMO-Annie",
#     "role": "admin"
#   },
#   "tenants": [
#     {
#       "tenant_id": "demo-annie",
#       "tenant_name": "DEMO-Annie",
#       "role": "admin"
#     }
#   ]
# }
```

**Nota:** El sistema automáticamente:
- Busca el usuario por `email`
- Obtiene todos sus tenants desde `user_tenants`
- Crea token con el primer tenant (o el que esté primero en orden)
- Devuelve lista completa de tenants disponibles

---

### Paso 3: Ver Settings Actuales (GET)

```bash
# GET /settings/general - RBAC: observer+ (admin puede leer)
curl -X GET "$API_BASE/api/v1/settings/general" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Respuesta si no existe (valores por defecto):
# {
#   "tenant_id": "demo-annie",
#   "name": "",
#   "logo_url": null,
#   "website_url": null,
#   "short_description": null,
#   "mission": null,
#   "vision": null,
#   "purpose": null,
#   "customer_problems": null,
#   "created_at": "",
#   "updated_at": ""
# }
```

---

### Paso 4: Autofill desde URL (POST)

```bash
# POST /settings/general/autofill-from-url - RBAC: admin+ (solo admin/owner)
AUTOFILL_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/settings/general/autofill-from-url" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "website_url": "https://example.com"
  }')

echo "$AUTOFILL_RESPONSE" | jq '.'

# Respuesta (sugerencias, NO persiste):
# {
#   "name": "Example Corp",
#   "short_description": "Leading provider of...",
#   "mission": "To empower businesses...",
#   "vision": "A world where...",
#   "purpose": "Our purpose is to...",
#   "customer_problems": "Businesses struggle with..."
# }
```

---

### Paso 5: Guardar Settings (PUT)

```bash
# PUT /settings/general - RBAC: admin+ (solo admin/owner puede escribir)
curl -X PUT "$API_BASE/api/v1/settings/general" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Annie",
    "logo_url": "https://cdn.example.com/demo/logo.png",
    "website_url": "https://demo.annie-ai.app",
    "short_description": "CRM con IA para equipos de ventas y atención al cliente",
    "mission": "Potenciar equipos de ventas con inteligencia artificial conversacional",
    "vision": "Ser la plataforma líder en automatización inteligente de conversaciones",
    "purpose": "Acelerar el crecimiento de negocios mediante IA conversacional",
    "customer_problems": "Baja tasa de conversión, respuesta lenta a clientes, falta de trazabilidad en conversaciones"
  }' | jq '.'

# Respuesta (settings actualizados):
# {
#   "tenant_id": "demo-annie",
#   "name": "Demo Annie",
#   "logo_url": "https://cdn.example.com/demo/logo.png",
#   ...
#   "created_at": "2024-01-15T10:30:00Z",
#   "updated_at": "2024-01-15T10:30:00Z"
# }
```

---

### Paso 6: Verificar Cambios (GET nuevamente)

```bash
# Verificar que se guardó correctamente
curl -X GET "$API_BASE/api/v1/settings/general" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

---

## 🔄 Cambiar de Tenant (si el usuario tiene múltiples)

Si el usuario `admin@demo.com` pertenece a múltiples tenants:

```bash
# POST /auth/switch-tenant
SWITCH_RESPONSE=$(curl -s -X POST "$API_BASE/api/v1/auth/switch-tenant" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "otro-tenant-id"
  }')

# Obtener nuevo token
NEW_TOKEN=$(echo "$SWITCH_RESPONSE" | jq -r '.token')

# Usar nuevo token para operaciones
TOKEN=$NEW_TOKEN
```

---

## 📊 Resumen del Flujo

```
1. Login (email + password)
   ↓
   Sistema busca usuario por email
   ↓
   Sistema obtiene tenants desde user_tenants
   ↓
   Devuelve token con primer tenant + lista de tenants

2. GET /settings/general (observer+)
   ↓
   Lee settings del tenant del token (auth.tenant_id)

3. POST /settings/general/autofill-from-url (admin+)
   ↓
   Extrae info de URL con LLM
   ↓
   Devuelve sugerencias (NO persiste)

4. PUT /settings/general (admin+)
   ↓
   Guarda settings en general_settings
   ↓
   Filtrado por tenant_id del token
```

---

## ✅ Puntos Clave

1. **Login NO pide tenant_id** - Solo email y password
2. **Tenant se obtiene automáticamente** - Desde `user_tenants` del usuario
3. **Token incluye tenant_id** - Del primer tenant del usuario
4. **RBAC por endpoint:**
   - GET: observer, agent, admin, owner
   - PUT/POST autofill: admin, owner
5. **Tenant isolation** - Todos los endpoints usan `auth.tenant_id` del token

