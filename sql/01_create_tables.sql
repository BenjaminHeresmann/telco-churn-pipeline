-- ============================================================
-- DDL: Esquema de base de datos para el pipeline Telco Churn
-- Asignatura: ITY1101 Gestion de Datos para IA - Duoc UC
-- ============================================================

-- Tabla principal: clientes y su churn
CREATE TABLE IF NOT EXISTS clientes (
    customer_id            VARCHAR(20)  PRIMARY KEY,
    gender                 VARCHAR(10)  NOT NULL CHECK (gender IN ('Male','Female')),
    senior_citizen         SMALLINT     NOT NULL CHECK (senior_citizen IN (0,1)),
    partner                BOOLEAN      NOT NULL,
    dependents             BOOLEAN      NOT NULL,
    tenure                 INTEGER      NOT NULL CHECK (tenure >= 0 AND tenure <= 100),
    phone_service          BOOLEAN      NOT NULL,
    multiple_lines         VARCHAR(20)  NOT NULL,
    internet_service       VARCHAR(20)  NOT NULL CHECK (internet_service IN ('DSL','Fiber optic','No')),
    online_security        VARCHAR(20)  NOT NULL,
    online_backup          VARCHAR(20)  NOT NULL,
    device_protection      VARCHAR(20)  NOT NULL,
    tech_support           VARCHAR(20)  NOT NULL,
    streaming_tv           VARCHAR(20)  NOT NULL,
    streaming_movies       VARCHAR(20)  NOT NULL,
    contract               VARCHAR(20)  NOT NULL CHECK (contract IN ('Month-to-month','One year','Two year')),
    paperless_billing      BOOLEAN      NOT NULL,
    payment_method         VARCHAR(30)  NOT NULL,
    monthly_charges        NUMERIC(8,2) NOT NULL CHECK (monthly_charges >= 0),
    total_charges          NUMERIC(10,2) CHECK (total_charges >= 0),
    tenure_group           VARCHAR(20),
    churn                  BOOLEAN      NOT NULL,
    fecha_ingesta          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clientes_churn    ON clientes(churn);
CREATE INDEX IF NOT EXISTS idx_clientes_contract ON clientes(contract);

-- Tabla de auditoria: registro de cada ejecucion del pipeline
CREATE TABLE IF NOT EXISTS carga_logs (
    id                     SERIAL       PRIMARY KEY,
    fecha_ejecucion        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archivo_origen         VARCHAR(255) NOT NULL,
    registros_leidos       INTEGER      NOT NULL,
    registros_insertados   INTEGER      NOT NULL,
    registros_rechazados   INTEGER      NOT NULL,
    duracion_segundos      NUMERIC(8,3) NOT NULL,
    estado                 VARCHAR(20)  NOT NULL CHECK (estado IN ('OK','ERROR','PARCIAL')),
    detalle_errores        TEXT
);

CREATE INDEX IF NOT EXISTS idx_carga_logs_fecha  ON carga_logs(fecha_ejecucion DESC);

-- Tabla opcional: registros rechazados (para auditoria de calidad)
CREATE TABLE IF NOT EXISTS clientes_rechazados (
    id                     SERIAL       PRIMARY KEY,
    customer_id            VARCHAR(20),
    payload                JSONB        NOT NULL,
    motivo_rechazo         TEXT         NOT NULL,
    tipo_validacion        VARCHAR(20)  NOT NULL CHECK (tipo_validacion IN ('estructural','semantica')),
    fecha_rechazo          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Seguridad: Row-Level Security (RLS)
-- Sin RLS, las tablas del esquema public quedan accesibles via la API REST
-- de Supabase (PostgREST) a cualquiera con la anon key. Se habilita RLS para
-- cerrar ese acceso. El backend se conecta como el rol dueno (postgres), que
-- IGNORA RLS, por lo que la carga/lectura del pipeline siguen funcionando.
-- Sin politicas permisivas => el rol anon/authenticated no tiene acceso.
-- ============================================================
ALTER TABLE clientes            ENABLE ROW LEVEL SECURITY;
ALTER TABLE carga_logs          ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes_rechazados ENABLE ROW LEVEL SECURITY;

-- Roles y permisos (ejemplo de control de acceso para el plan de seguridad)
-- Estos comandos se ejecutan opcionalmente con un superusuario
-- CREATE ROLE telco_analista LOGIN PASSWORD 'cambiar';
-- GRANT SELECT ON clientes TO telco_analista;
-- REVOKE INSERT, UPDATE, DELETE ON clientes FROM telco_analista;
