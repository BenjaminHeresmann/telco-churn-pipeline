# Auditoría de seguridad del pipeline y su entorno — Evaluación 3

**Proyecto:** Telco Customer Churn · **Asignatura:** ITY1101 Gestión de Datos para IA (Duoc UC)
**Stack auditado:** GitHub (repo público) · Railway (API FastAPI, 1 contenedor) · Supabase (PostgreSQL 17)
**Fecha:** 2026-06-28 · **Enfoque:** *compliance / privacy by design* hacia la Ley 21.719

> La auditoría se organiza en los **4 frentes** que enseña el material (3.3): credenciales,
> accesos y permisos, entorno/dependencias y logs de seguridad. Cada hallazgo se acompaña
> de evidencia reproducible y de una mitigación clasificada como **preventiva** o **correctiva**.

---

## Resumen ejecutivo
El sistema no expone credenciales en el código ni en el historial de git, y la base de datos
está **cerrada por defecto** (RLS activo, sin políticas; los roles públicos `anon`/`authenticated`
no acceden). El único hallazgo accionable es **dependencias desactualizadas con CVEs conocidos**
(detectadas con `pip-audit`), con plan de actualización. Todos los controles se mapean a principios
de la Ley 19.628 modernizada por la **Ley 21.719** (vigencia plena 01-12-2026, nivel GDPR).

---

## Frente 1 — Credenciales y secretos
**Objetivo:** que ninguna clave/contraseña/token viva en el código ni en el repositorio público.

| Verificación | Comando | Resultado |
|---|---|---|
| Secretos hardcodeados en código | `grep -i "password\|token\|secret\|sbp_\|service_role"` | Solo **placeholders** (`tu_password`, `[YOUR-PASSWORD]`, `'CAMBIAR'`) y lecturas `os.getenv(...)`. **0 secretos reales.** |
| `.env` ignorado por git | `cat .gitignore` | `.env` y `.env.local` excluidos (línea 16). ✅ |
| `.env` en el historial | `git log --all -- .env` | Nunca commiteado. ✅ |
| Password real en algún commit | `git log --all -S '<password>' --oneline` | **0 commits.** ✅ |

**Diseño:** las credenciales viven solo en variables de entorno (Railway y Supabase) y en el
`.env` local (gitignored). El backend las lee con `os.getenv("DATABASE_URL")`. La conexión a
Supabase fuerza `sslmode=require` (cifrado en tránsito, TLS).

**Mitigación (preventiva):** rotar y **revocar todos los tokens tras la evaluación** (Supabase,
Railway, Vercel). Mantener el patrón "secretos solo en el entorno, nunca en el repo".

---

## Frente 2 — Accesos y permisos (privilegio mínimo)
**Objetivo:** que cada actor tenga solo los permisos necesarios y que la BD no sea pública.

**Estado de Row-Level Security (verificado en `pg_tables`/`pg_policies`):**

| Tabla | RLS activo | Nº políticas | Efecto |
|---|---|---|---|
| `clientes` | ✅ true | 0 | cerrado por defecto |
| `predicciones` | ✅ true | 0 | cerrado por defecto |
| `carga_logs` | ✅ true | 0 | cerrado por defecto |
| `clientes_rechazados` | ✅ true | 0 | cerrado por defecto |

**Roles (verificado en `pg_roles`):**
- `postgres` (rol del pipeline): `rolbypassrls = true` → es el **dueño**, por eso la ingesta/carga
  funcionan. No es superusuario.
- `anon` y `authenticated` (acceso público vía API REST de Supabase): `rolcanlogin = false`,
  `rolbypassrls = false` → **no pueden bypassear RLS**; con 0 políticas **no leen ningún dato**.
- `service_role`: bypassa RLS pero no es de login público (uso interno del backend).

**Conclusión:** la base **no es accesible públicamente**; solo el backend (rol dueño) lee/escribe.
El *advisor* de seguridad de Supabase reporta 0 vulnerabilidades (4 notas `INFO: RLS enabled, no
policy`, que es justamente la postura buscada).

**Diseño de privilegio mínimo (`sql/02_roles_seguridad.sql`):** rol `telco_lectura` de **solo
lectura** para la analítica/dashboard (SELECT en `clientes` y `predicciones`, sin escritura). En
producción el dashboard se conectaría como ese rol, **no** como el dueño.

**Mitigación (preventiva):** aplicar `02_roles_seguridad.sql` y apuntar el dashboard al rol de
solo lectura; mantener la separación dueño-escritura / analítica-lectura.

---

## Frente 3 — Entorno de ejecución y dependencias
**Objetivo:** detectar librerías/imágenes con vulnerabilidades conocidas y configuraciones inseguras.

**Escaneo de dependencias (`pip-audit -r requirements.txt`):** **10 vulnerabilidades en 3 paquetes.**

| Paquete | Versión | CVE / ID | Corrige en | Criticidad para el proyecto |
|---|---|---|---|---|
| `starlette` | 0.36.3 | CVE-2024-47874 y 6 más | 0.40.0 → 1.x | Transitiva de FastAPI 0.110; acoplada (subirla exige subir FastAPI) |
| `python-dotenv` | 1.0.0 | CVE-2026-28684 | 1.2.2 | Lee `.env`; actualización directa y segura |
| `pytest` | 7.4.4 | CVE-2025-71176 | 9.0.3 | Solo dependencia de **desarrollo/test**, no de runtime |

**Herramienta para imágenes/contenedores:** `trivy` (referenciada en el material 3.3 y en la
formativa) escanea imágenes Docker y librerías. Como el despliegue es *cloud-only* (Railway
construye la imagen; Docker no está instalado localmente), el equivalente gestionado aplicado es
**`pip-audit` sobre las dependencias + escaneo del repositorio**; `trivy` se propone para escanear
la imagen que Railway construye.

**Exposición de red:** Supabase exige TLS/SSL y autenticación (no acepta conexiones anónimas a la
BD); Railway expone solo el puerto HTTPS del servicio FastAPI. No hay puertos de BD abiertos a
Internet.

**Mitigación:** **(correctiva)** actualizar `python-dotenv` a 1.2.2; **(preventiva)** planificar la
actualización conjunta FastAPI+Starlette y ejecutar `pip-audit`/`trivy` de forma periódica.

---

## Frente 4 — Logs de seguridad
**Objetivo:** distinguir el monitoreo de **rendimiento** del monitoreo de **seguridad**.

- `carga_logs` (auditoría del pipeline) registra cada corrida: archivo origen, registros
  leídos/insertados/rechazados, duración y estado → trazabilidad e integridad del dato.
- **Lectura de seguridad** (material 3.3 + formativa): en los logs de Railway/Supabase,
  **accesos fallidos repetidos = posible intento de fuerza bruta/intrusión** (no un error benigno).
  Se deben clasificar eventos **críticos** (accesos denegados, errores de autenticación) vs
  **advertencias** (latencia, reintentos).

**Mitigación (preventiva):** revisar periódicamente los logs de acceso del proyecto Supabase y del
servicio Railway; alertar ante picos de accesos fallidos.

---

## Mapeo a la normativa chilena — Ley 19.628 / Ley 21.719 (*compliance by design*)
En Chile la protección de datos personales se rige por la **Ley 19.628**, reformada y modernizada
integralmente por la **Ley 21.719**, que eleva los estándares al nivel europeo (**GDPR**) y entra
en **aplicación plena el 01-12-2026**. El sistema se construyó **desde su diseño** para cumplirla.

**Clasificación de los datos del caso Telco:**
- **Datos personales** (identifican o se relacionan con una persona): `customerID` (identificador),
  `gender`, `SeniorCitizen` (rango etario), `Partner`/`Dependents` (situación familiar),
  `tenure`/`Contract`/cargos/`PaymentMethod` (datos económicos y de la relación contractual).
- **Datos sensibles** (categorías especiales 21.719: salud, biometría, ideología, etc.):
  **el dataset NO contiene** datos sensibles en sentido estricto, pero sí datos personales
  económicos/conductuales que exigen protección.

**Controles técnicos ↔ principios de la ley:**

| Principio (Ley 21.719 / GDPR) | Control implementado |
|---|---|
| **Finalidad y proporcionalidad** | Los datos se usan solo para predecir churn (fin declarado); no se recolectan campos extra. |
| **Minimización** | `customerID` es un identificador, no nombre/RUT; el modelo usa solo variables necesarias. |
| **Seguridad y confidencialidad** | RLS cerrado por defecto, privilegio mínimo, TLS en tránsito, secretos fuera del código. |
| **Calidad / integridad del dato** | Pipeline de limpieza+validación (Eval 2) + auditoría en `carga_logs`. |
| **Responsabilidad proactiva** (*accountability*, nuevo en 21.719) | Controles embebidos desde el diseño; esta auditoría es evidencia de cumplimiento. |
| **Derechos ARCO** (acceso, rectificación, cancelación, oposición) | El pipeline indexa por `customer_id` y opera *full-refresh*, lo que permite rectificar/eliminar a un titular. |

**Reflexión CIA:** *Confidencialidad* (RLS + privilegio mínimo + TLS), *Integridad* (validación +
transacciones + auditoría), *Disponibilidad* (servicio gestionado Supabase/Railway; riesgo: el free
tier se suspende por inactividad → mitigación: mantener activos antes de operar/demostrar).

---

## Tabla resumen: hallazgo → mitigación

| # | Hallazgo | Severidad | Mitigación | Tipo |
|---|---|---|---|---|
| 1 | Sin secretos en código/historial | — (OK) | Mantener patrón; revocar tokens post-evaluación | Preventiva |
| 2 | BD cerrada por defecto (RLS) | — (OK) | Aplicar rol de solo lectura para el dashboard | Preventiva |
| 3 | 10 CVEs en dependencias (starlette/dotenv/pytest) | Media | Actualizar `python-dotenv`; planear FastAPI+Starlette | Correctiva + Preventiva |
| 4 | Logs no monitoreados por seguridad | Baja | Revisar accesos fallidos (fuerza bruta) periódicamente | Preventiva |
| 5 | Free tier se suspende (disponibilidad) | Baja | Despertar servicios antes de operar/demostrar | Preventiva |

---

### Evidencia y reproducibilidad
- `pip-audit -r requirements.txt` → ver salida en `outputs/seguridad/pip_audit.txt`.
- Estado RLS y roles → consultas a `pg_tables`, `pg_policies`, `pg_roles` (Supabase).
- Diseño de roles → `sql/01_create_tables.sql` (RLS) y `sql/02_roles_seguridad.sql` (privilegio mínimo).
