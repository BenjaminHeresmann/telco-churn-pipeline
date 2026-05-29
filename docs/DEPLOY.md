# Guía de Despliegue Cloud — Supabase + Railway

Tiempo total estimado: **20-30 minutos** la primera vez.

---

## Parte 1 — Supabase (10 min)

### 1.1 Crear proyecto

1. Ir a https://supabase.com → "Start your project" → login con GitHub
2. "New Project":
   - Name: `telco-churn-data`
   - Database Password: **generar y guardar** (es la contraseña de Postgres)
   - Region: la más cercana (ej. `us-east-1`)
   - Pricing Plan: Free
3. Esperar ~2 min mientras Supabase aprovisiona el Postgres

### 1.2 Crear las tablas (ejecutar DDL)

1. En el dashboard de Supabase, panel izquierdo → **SQL Editor**
2. Click "New query"
3. Copiar TODO el contenido del archivo `sql/01_create_tables.sql` del repo
4. Pegar en el editor → click "Run" (Ctrl+Enter)
5. Debería decir "Success. No rows returned"
6. Verificar en panel izquierdo → **Table Editor** → deberían aparecer:
   - `clientes` (vacía)
   - `carga_logs` (vacía)
   - `clientes_rechazados` (vacía)

### 1.3 Configurar Storage para el CSV fuente

1. Panel izquierdo → **Storage** → "New bucket"
2. Nombre: `telco-data`
3. Marcar "Public bucket" (para simplificar; en producción usar policies)
4. "Create bucket"
5. Click en el bucket `telco-data` → "Upload file"
6. Subir el CSV `02_Base_WA_Fn-UseC_-Telco-Customer-Churn.csv` desde la carpeta del curso
7. **Renombrarlo a `telco_churn_source.csv`** (más simple para el .env)

### 1.4 Obtener credenciales

**A. Connection String (para Postgres directo):**
1. Panel izquierdo → **Settings** (icono engranaje) → **Database**
2. Buscar sección "Connection string" → seleccionar tab **URI**
3. **IMPORTANTE:** elegir modo **"Transaction"** (Pooler en puerto 6543, mejor para apps serverless)
4. Copiar el connection string completo (algo así):
   ```
   postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```
5. Reemplazar `[YOUR-PASSWORD]` por la contraseña que generaste en 1.1

**B. URL y API Key (para Storage):**
1. Panel izquierdo → **Settings** → **API**
2. Copiar:
   - **Project URL** (ej `https://xxxxx.supabase.co`)
   - **anon public key** (string largo que empieza con `eyJhbGc...`)

> 🔒 La `service_role` key tiene permisos full y NO debe usarse desde el frontend ni commitear. Para el pipeline backend (Railway) puedes usarla o la `anon` con políticas adecuadas.

---

## Parte 2 — Railway (10 min)

### 2.1 Conectar el repo

1. Ir a https://railway.app → "Login with GitHub"
2. "New Project" → "Deploy from GitHub repo"
3. Autorizar Railway a leer tus repos (la primera vez)
4. Seleccionar el repo `telco-churn-pipeline`
5. Railway detectará el `Dockerfile` y empezará el primer build automáticamente

### 2.2 Configurar variables de entorno

Mientras buildea, ir a "Variables" del servicio y agregar:

```
DATABASE_URL=postgresql://postgres.xxxxx:tu_password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...
SUPABASE_BUCKET=telco-data
SOURCE_CSV_FILENAME=telco_churn_source.csv
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

> Tip: en Railway puedes pegar todo de una vez con "Raw Editor".

### 2.3 Generar dominio público

1. "Settings" del servicio → sección **Networking** → "Generate Domain"
2. Railway te dará una URL tipo `https://telco-churn-pipeline-production-xxxx.up.railway.app`
3. Guarda esta URL — es la pública de tu API

### 2.4 Verificar deploy

Esperar ~2 minutos a que termine el build y el deploy. Luego:

```bash
curl https://<tu-url>.up.railway.app/health
```

Respuesta esperada (con BD conectada):
```json
{
  "status": "healthy",
  "database": "ok",
  "database_error": null,
  "timestamp": 1779843768.42
}
```

Si dice `degraded`, revisar los logs en Railway → tab "Deployments" → click en el deployment → "View Logs". El error te dirá qué credencial está mal.

---

## Parte 3 — Probar end-to-end (5 min)

### 3.1 Vía Swagger UI (recomendado para demo)

1. Abrir en navegador: `https://<tu-url>.up.railway.app/docs`
2. Verás la interfaz Swagger con todos los endpoints
3. Click en `POST /pipeline/run` → "Try it out" → "Execute"
4. Esperar 10-30 seg → deberías ver respuesta `200 OK` con resumen de las 4 etapas

### 3.2 Vía curl

```bash
URL=https://<tu-url>.up.railway.app

# Ejecutar pipeline completo
curl -X POST $URL/pipeline/run | python -m json.tool

# Ver KPIs agregados
curl $URL/kpis/resumen | python -m json.tool

# Ver últimos rechazados
curl $URL/rechazados?limit=10 | python -m json.tool
```

### 3.3 Verificar en Supabase

1. Supabase → Table Editor → `clientes` → deberías ver 7.043 registros
2. Tabla `carga_logs` → 1 registro con `estado='OK'` y `registros_insertados=7043`

---

## Parte 4 — CI (GitHub Actions) y CD (Railway)

**CI — automático.** Configurado en `.github/workflows/ci.yml`. Cada push a `main`
dispara GitHub Actions que corre `pytest tests/`. Verás el badge verde en el commit
cuando pasa.

**CD — manual.** El deploy a Railway se hace con un comando desde la raíz del repo:

```bash
railway up --detach --service telco-api   # con RAILWAY_API_TOKEN en el entorno
```

Se eligió deploy manual (gate humano) en vez de auto-deploy para controlar
exactamente qué versión llega a producción. **Para activar auto-deploy** (deploy en
cada push), basta conectar el repo de GitHub al servicio desde el dashboard de
Railway (Settings → Source → Connect Repo); a partir de ahí Railway redespliega solo.

Para exigir que los tests pasen antes de poder mergear:
1. GitHub → Settings → Branches → Add rule para `main`
2. "Require status checks to pass before merging" → seleccionar `test`

---

## Troubleshooting

### "Connection refused" en `/health`
- Verificar `DATABASE_URL` exacto (copia del Supabase, ojo con el puerto 6543 vs 5432)
- Verificar que el password no tiene caracteres especiales sin URL-encode
- En Supabase, verificar que el proyecto está "Healthy" (no pausado por inactividad en plan free)

### "Bucket not found" en `/pipeline/ingest`
- Verificar `SUPABASE_BUCKET` matches el nombre exacto del bucket
- Verificar que el archivo existe con el nombre `SOURCE_CSV_FILENAME`
- Verificar que el bucket es público o que la `SUPABASE_KEY` tiene permisos

### Railway build falla
- Logs → buscar líneas con `ERROR`
- Si es por pip, verificar `requirements.txt` localmente con `pip install -r requirements.txt`
- Si es por Dockerfile, probar `docker build .` localmente

### "Module not found" en Railway
- Confirmar que el código está en `src/` y el Dockerfile copia `COPY src/ ./src/`
- Confirmar que el comando de inicio es `uvicorn src.api:app ...`

### Tests de GitHub Actions fallan
- Probar localmente: `pytest tests/ -v`
- Si pasan local pero fallan en CI, suele ser por Python version mismatch — revisar `ci.yml`

---

## Checklist final pre-evaluación

- [ ] Supabase con 3 tablas creadas y bucket con CSV
- [ ] Railway desplegado con dominio público funcionando
- [ ] `/health` responde `"status": "healthy"`
- [ ] `/pipeline/run` ejecuta y devuelve 200
- [ ] Supabase Table Editor muestra 7.043 filas en `clientes`
- [ ] GitHub Actions corriendo verde
- [ ] README actualizado con la URL de Railway
- [ ] Plan de demo ensayado al menos una vez
