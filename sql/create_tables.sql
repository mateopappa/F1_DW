-- ============================================================================
-- F1 DATA WAREHOUSE - DDL (Data Definition Language)
-- Metodología: Hefesto
-- Modelo: Esquema Estrella (Star Schema)
-- Base de Datos: MySQL
-- ============================================================================

-- Crear base de datos si no existe
CREATE DATABASE IF NOT EXISTS f1_datawarehouse;
USE f1_datawarehouse;

-- Eliminar tablas si existen (para poder recrear)
DROP TABLE IF EXISTS fact_resultado_carrera;
DROP TABLE IF EXISTS dim_carrera;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_piloto;
DROP TABLE IF EXISTS dim_constructor;
DROP TABLE IF EXISTS dim_circuito;

-- ============================================================================
-- PASO 1: CREAR DIMENSIONES (Tablas más simples primero)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- DIMENSIÓN: PILOTO
-- Fuente: drivers.csv
-- Descripción: Información de los pilotos de F1
-- ----------------------------------------------------------------------------
CREATE TABLE dim_piloto (
    piloto_id        INT PRIMARY KEY,
    nombre           VARCHAR(100),
    apellido         VARCHAR(100),
    nombre_completo  VARCHAR(200),
    codigo           VARCHAR(3),
    numero           INT,
    nacionalidad     VARCHAR(50),
    fecha_nacimiento DATE,
    url              TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Dimensión de pilotos de Fórmula 1';

-- ----------------------------------------------------------------------------
-- DIMENSIÓN: CONSTRUCTOR
-- Fuente: constructors.csv
-- Descripción: Equipos/Escuderías de F1
-- ----------------------------------------------------------------------------
CREATE TABLE dim_constructor (
    constructor_id   INT PRIMARY KEY,
    nombre           VARCHAR(100),
    referencia       VARCHAR(50),
    nacionalidad     VARCHAR(50),
    url              TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Dimensión de constructores/equipos de F1';

-- ----------------------------------------------------------------------------
-- DIMENSIÓN: CIRCUITO
-- Fuente: circuits.csv
-- Descripción: Circuitos donde se corren los GPs
-- ----------------------------------------------------------------------------
CREATE TABLE dim_circuito (
    circuito_id      INT PRIMARY KEY,
    nombre           VARCHAR(100),
    ubicacion        VARCHAR(100),
    pais             VARCHAR(50),
    latitud          DECIMAL(10,6),
    longitud         DECIMAL(10,6),
    altitud          INT,
    url              TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Dimensión de circuitos de F1';

-- ----------------------------------------------------------------------------
-- DIMENSIÓN: TIEMPO
-- Fuente: Derivada de races.csv (columna date)
-- Descripción: Dimensión temporal con jerarquías
-- ----------------------------------------------------------------------------
CREATE TABLE dim_tiempo (
    tiempo_id        INT PRIMARY KEY,
    fecha            DATE,
    anio             INT,
    mes              INT,
    dia              INT,
    trimestre        INT,
    decada           INT,
    nombre_mes       VARCHAR(20),
    dia_semana       VARCHAR(20),
    es_fin_semana    BOOLEAN
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Dimensión temporal (fechas de carreras)';

-- ----------------------------------------------------------------------------
-- DIMENSIÓN: CARRERA
-- Fuente: races.csv
-- Descripción: Grandes Premios (tiene FK a circuito)
-- ----------------------------------------------------------------------------
CREATE TABLE dim_carrera (
    carrera_id       INT PRIMARY KEY,
    anio             INT,
    ronda            INT,
    circuito_id      INT,
    nombre_gp        VARCHAR(100),
    fecha            DATE,
    hora             TIME,
    url              TEXT,
    
    -- Foreign Key: Una carrera se corre en un circuito
    FOREIGN KEY (circuito_id) REFERENCES dim_circuito(circuito_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Dimensión de carreras/Grandes Premios';

-- ============================================================================
-- PASO 2: CREAR TABLA DE HECHOS
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLA DE HECHOS: RESULTADO DE CARRERA
-- Fuente: results.csv
-- Descripción: Métricas de cada piloto en cada carrera
-- Granularidad: Un registro = Un piloto en una carrera específica
-- ----------------------------------------------------------------------------
CREATE TABLE fact_resultado_carrera (
    -- CLAVES FORÁNEAS (Dimensiones)
    carrera_id           INT NOT NULL,
    piloto_id            INT NOT NULL,
    constructor_id       INT NOT NULL,
    circuito_id          INT NOT NULL,
    tiempo_id            INT NOT NULL,
    
    -- MÉTRICAS NUMÉRICAS
    puntos               DECIMAL(5,2),
    posicion_final       INT,
    posicion_salida      INT,
    vueltas_completadas  INT,
    tiempo_final_ms      BIGINT,
    
    -- MÉTRICAS ADICIONALES
    mejor_vuelta         INT,
    tiempo_mejor_vuelta  INT,
    velocidad_promedio   DECIMAL(6,2),
    
    -- MÉTRICAS DERIVADAS (Calculadas en ETL)
    es_victoria          BOOLEAN,
    es_podio             BOOLEAN,
    es_pole              BOOLEAN,
    es_punto             BOOLEAN,
    completo_carrera     BOOLEAN,
    
    -- CLAVE PRIMARIA COMPUESTA
    PRIMARY KEY (carrera_id, piloto_id),
    
    -- FOREIGN KEYS
    FOREIGN KEY (carrera_id) REFERENCES dim_carrera(carrera_id),
    FOREIGN KEY (piloto_id) REFERENCES dim_piloto(piloto_id),
    FOREIGN KEY (constructor_id) REFERENCES dim_constructor(constructor_id),
    FOREIGN KEY (circuito_id) REFERENCES dim_circuito(circuito_id),
    FOREIGN KEY (tiempo_id) REFERENCES dim_tiempo(tiempo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Tabla de hechos: Resultados de pilotos por carrera';

-- ============================================================================
-- PASO 3: CREAR ÍNDICES (Para optimizar consultas)
-- ============================================================================

-- Índices en tabla de hechos (las más consultadas)
CREATE INDEX idx_fact_piloto ON fact_resultado_carrera(piloto_id);
CREATE INDEX idx_fact_constructor ON fact_resultado_carrera(constructor_id);
CREATE INDEX idx_fact_circuito ON fact_resultado_carrera(circuito_id);
CREATE INDEX idx_fact_tiempo ON fact_resultado_carrera(tiempo_id);
CREATE INDEX idx_fact_victoria ON fact_resultado_carrera(es_victoria);
CREATE INDEX idx_fact_podio ON fact_resultado_carrera(es_podio);

-- Índices en dimensiones
CREATE INDEX idx_carrera_anio ON dim_carrera(anio);
CREATE INDEX idx_tiempo_anio ON dim_tiempo(anio);
CREATE INDEX idx_tiempo_decada ON dim_tiempo(decada);
CREATE INDEX idx_piloto_nombre ON dim_piloto(nombre_completo);

-- ============================================================================
-- ✅ DDL COMPLETADO!
-- Total: 5 dimensiones + 1 tabla de hechos + índices
-- ============================================================================


