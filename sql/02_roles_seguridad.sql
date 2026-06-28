-- ============================================================
-- Seguridad: roles de acceso de privilegio minimo (Evaluacion 3)
-- Asignatura: ITY1101 Gestion de Datos para IA - Duoc UC
--
-- Principio de PRIVILEGIO MINIMO (least privilege): cada actor recibe solo
-- los permisos estrictamente necesarios. Implementa la indicacion del
-- cuestionario formativo ("definir roles de acceso minimo, roles de BD") y
-- el deber de la Ley 21.719 de limitar el acceso a datos personales.
--
-- MODELO DE ACCESO (dos capas):
--   Capa 1 - RLS: todas las tablas tienen Row-Level Security ACTIVO y SIN
--     politicas permisivas => cerrado por defecto. Los roles `anon` y
--     `authenticated` (acceso publico de la API REST de Supabase) NO pueden
--     loguear ni bypassear RLS, por lo que NO leen nada.
--   Capa 2 - Roles/GRANT: el pipeline backend (ingesta->carga) se conecta con
--     el rol dueno `postgres`, que bypassea RLS y tiene escritura. La analitica
--     y el dashboard BI deberian usar un rol de SOLO LECTURA, nunca el dueno.
--
-- Este script define ese rol de solo lectura. Es la configuracion objetivo de
-- endurecimiento (hardening) para produccion: el dashboard se conectaria como
-- `telco_lectura` en vez del rol dueno. Ejecutar con un rol privilegiado.
-- ============================================================

-- 1) Rol de SOLO LECTURA para analitica / dashboard BI (sin escritura)
DROP ROLE IF EXISTS telco_lectura;
CREATE ROLE telco_lectura LOGIN PASSWORD 'CAMBIAR_EN_PRODUCCION';  -- rotar; nunca commitear el valor real

-- 2) Acceso de lectura SOLO a las tablas necesarias (no a auditoria interna)
GRANT USAGE ON SCHEMA public TO telco_lectura;
GRANT SELECT ON clientes     TO telco_lectura;
GRANT SELECT ON predicciones TO telco_lectura;

-- 3) Se NIEGA explicitamente toda escritura (defensa en profundidad)
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM telco_lectura;

-- 4) Politica RLS que habilita la LECTURA de ese rol a traves de RLS,
--    manteniendo el resto cerrado. El rol dueno sigue bypaseando RLS.
DROP POLICY IF EXISTS lectura_analitica ON predicciones;
CREATE POLICY lectura_analitica ON predicciones
    FOR SELECT TO telco_lectura USING (true);

DROP POLICY IF EXISTS lectura_clientes ON clientes;
CREATE POLICY lectura_clientes ON clientes
    FOR SELECT TO telco_lectura USING (true);

-- Verificacion (privilegio minimo):
--   SET ROLE telco_lectura;  SELECT count(*) FROM predicciones;   -- OK
--   SET ROLE telco_lectura;  INSERT INTO clientes DEFAULT VALUES; -- ERROR: permiso denegado
--   RESET ROLE;
--
-- Para revocar tras la evaluacion:
--   DROP POLICY lectura_analitica ON predicciones;
--   DROP POLICY lectura_clientes  ON clientes;
--   DROP ROLE telco_lectura;
