# Guía de Deployment - Annie-AI Backend

## 🚀 Actualizar Código en Servidor

### Opción 1: Deployment Manual (SSH)

#### 1. Conectarse al Servidor

```bash
ssh usuario@tu-servidor.com
# O si usas clave específica:
ssh -i ~/.ssh/tu-clave.pem usuario@tu-servidor.com
```

#### 2. Ir al Directorio del Proyecto

```bash
cd /ruta/a/back-annie
# Ejemplo común:
cd ~/back-annie
# O si está en /opt:
cd /opt/back-annie
```

#### 3. Hacer Pull del Código

```bash
# Verificar que estás en la rama correcta
git branch

# Hacer pull de los cambios
git pull origin main
# O si usas otra rama:
git pull origin develop
```

#### 4. Ejecutar Migraciones SQL

```bash
# Conectar a PostgreSQL y ejecutar migraciones
psql -h localhost -U postgres -d annie_db -f app/db/general_settings_schema.sql

# O si usas PostgreSQL managed (con URL):
psql $DATABASE_URL -f app/db/general_settings_schema.sql

# Verificar que la tabla se creó:
psql $DATABASE_URL -c "\d general_settings"
```

#### 5. Instalar/Actualizar Dependencias

**Si usas Docker Compose (recomendado):**

```bash
# Reconstruir imagen con nuevas dependencias
docker-compose build

# O si solo cambió requirements.txt:
docker-compose build --no-cache app
```

**Si NO usas Docker (Python directo):**

```bash
# Activar entorno virtual (si usas)
source venv/bin/activate

# Instalar nuevas dependencias
pip install -r app/requirements.txt

# O actualizar todo:
pip install --upgrade -r app/requirements.txt
```

#### 6. Reiniciar Servicios

**Docker Compose:**

```bash
# Reiniciar solo el servicio de la app
docker-compose restart app

# O hacer restart completo:
docker-compose down
docker-compose up -d

# Ver logs para verificar:
docker-compose logs -f app
```

**Systemd (si usas servicio):**

```bash
# Reiniciar servicio
sudo systemctl restart annie-api

# Ver estado
sudo systemctl status annie-api

# Ver logs
sudo journalctl -u annie-api -f
```

**Gunicorn/Uvicorn directo:**

```bash
# Si usas supervisor:
sudo supervisorctl restart annie-api

# Si usas PM2:
pm2 restart annie-api

# Si lo ejecutas manualmente, detener y reiniciar:
pkill -f "uvicorn app.main:app"
# Luego iniciar de nuevo según tu setup
```

---

### Opción 2: Script de Deployment Automatizado

Crea un script `deploy.sh` en el servidor:

```bash
#!/bin/bash
set -e  # Salir si hay error

echo "🚀 Iniciando deployment..."

# 1. Ir al directorio
cd /ruta/a/back-annie

# 2. Pull del código
echo "📥 Actualizando código..."
git pull origin main

# 3. Ejecutar migraciones
echo "🗄️ Ejecutando migraciones..."
psql $DATABASE_URL -f app/db/general_settings_schema.sql || echo "⚠️ Migración ya existe o error"

# 4. Reconstruir Docker (si aplica)
if [ -f docker-compose.yml ]; then
    echo "🐳 Reconstruyendo contenedores..."
    docker-compose build app
    docker-compose up -d app
    echo "✅ Contenedores reiniciados"
else
    # 5. Actualizar dependencias Python
    echo "📦 Actualizando dependencias..."
    source venv/bin/activate  # Si usas venv
    pip install -r app/requirements.txt
    
    # 6. Reiniciar servicio
    echo "🔄 Reiniciando servicio..."
    sudo systemctl restart annie-api || supervisorctl restart annie-api
fi

# 7. Verificar salud
echo "🏥 Verificando salud..."
sleep 2
curl -f http://localhost:8000/health || echo "⚠️ Health check falló"

echo "✅ Deployment completado!"
```

Hacer ejecutable y usar:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

### Opción 3: CI/CD con GitHub Actions / GitLab CI

**GitHub Actions (`.github/workflows/deploy.yml`):**

```yaml
name: Deploy to Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /ruta/a/back-annie
            git pull origin main
            docker-compose build app
            docker-compose up -d app
            docker-compose exec -T app psql $DATABASE_URL -f app/db/general_settings_schema.sql || true
```

---

## 📋 Checklist de Deployment

### Antes de Deployar

- [ ] Código subido a Git
- [ ] Migraciones SQL probadas localmente
- [ ] Variables de entorno configuradas en servidor
- [ ] Backup de base de datos (opcional pero recomendado)

### Durante Deployment

- [ ] `git pull` exitoso
- [ ] Migraciones ejecutadas sin errores
- [ ] Dependencias instaladas/actualizadas
- [ ] Servicios reiniciados

### Después de Deployar

- [ ] Health check: `curl http://api.annie-ai.app/health`
- [ ] Verificar logs: `docker-compose logs app` o `journalctl -u annie-api`
- [ ] Probar endpoint: `GET /api/v1/settings/general`
- [ ] Verificar que nuevas tablas existen en DB

---

## 🔧 Comandos Útiles

### Verificar Estado

```bash
# Ver logs en tiempo real
docker-compose logs -f app

# Ver estado de contenedores
docker-compose ps

# Verificar que la app responde
curl http://localhost:8000/health

# Verificar variables de entorno
docker-compose exec app env | grep -E "DATABASE|JWT|OPENAI"
```

### Rollback (si algo falla)

```bash
# Volver a commit anterior
git log --oneline  # Ver commits
git checkout <commit-anterior>
docker-compose build app
docker-compose up -d app
```

### Verificar Base de Datos

```bash
# Conectar a PostgreSQL
psql $DATABASE_URL

# Verificar tabla general_settings
\d general_settings

# Ver datos
SELECT * FROM general_settings LIMIT 1;
```

---

## 🐳 Docker Compose Específico

Si tu `docker-compose.yml` es algo como:

```yaml
version: '3.8'
services:
  app:
    build: ./app
    volumes:
      - ./app:/app
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8000:8000"
```

**Comandos de deployment:**

```bash
# 1. Pull código
git pull

# 2. Rebuild (si cambió Dockerfile o requirements.txt)
docker-compose build app

# 3. Restart
docker-compose restart app

# 4. Migraciones (dentro del contenedor)
docker-compose exec app psql $DATABASE_URL -f app/db/general_settings_schema.sql

# 5. Verificar
docker-compose logs -f app
```

---

## ⚠️ Notas Importantes

1. **Variables de Entorno**: Asegúrate de que `.env` o variables de entorno estén configuradas:
   - `DATABASE_URL` o `PG_HOST`, `PG_USER`, `PG_PASSWORD`, etc.
   - `JWT_SECRET`
   - `OPENAI_API_KEY` (para autofill)
   - `REDIS_HOST`, `REDIS_PASSWORD` (si usas)

2. **Migraciones**: Ejecuta migraciones ANTES de reiniciar servicios si hay cambios en schema

3. **Dependencias**: Si agregaste `beautifulsoup4`, asegúrate de que se instale:
   ```bash
   pip install beautifulsoup4==4.12.3
   # O en Docker, rebuild
   ```

4. **Backup**: Antes de migraciones importantes:
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
   ```

---

## 🚨 Troubleshooting

### Error: "Table already exists"
```bash
# La migración ya se ejecutó, es normal
# Puedes ignorar o usar IF NOT EXISTS en SQL
```

### Error: "Module not found: beautifulsoup4"
```bash
# Reinstalar dependencias
pip install -r app/requirements.txt
# O rebuild Docker
docker-compose build --no-cache app
```

### Error: "Connection refused" en health check
```bash
# Verificar que el servicio está corriendo
docker-compose ps
# Ver logs
docker-compose logs app
# Verificar puerto
netstat -tulpn | grep 8000
```

### Error: "JWT_SECRET not found"
```bash
# Verificar variables de entorno
docker-compose exec app env | grep JWT
# O en .env file
cat .env | grep JWT
```

