# F1 Data Warehouse 🏎️

Data Warehouse de Fórmula 1 utilizando **Metodología Hefesto** + **MySQL**

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.8 o superior
- MySQL 8.0 o superior
- pip (gestor de paquetes Python)

### Paso 1: Instalar MySQL
```bash
# macOS (con Homebrew)
brew install mysql
brew services start mysql

# Crear usuario y base de datos
mysql -u root -p
```

### Paso 2: Instalar Dependencias Python
```bash
# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# Instalar dependencias
pip install -r requirements.txt
```



### Paso 3: Ejecutar ETL
```bash
python3 etl.py
```

El proceso ETL:
1. ✅ Crea el esquema (5 dimensiones + 1 tabla de hechos)
2. ✅ Carga dimensiones (pilotos, constructores, circuitos, tiempo, carreras)
3. ✅ Carga hechos (~26,000 resultados de carreras)
4. ✅ Verifica integridad referencial

---

## 📊 FASE 1: ANÁLISIS DE REQUISITOS

### Preguntas de Negocio (14 preguntas identificadas)

#### 🏆 Campeonatos y Dominancia
1. **¿Quién es el piloto que más campeonatos ganó?**
2. **¿Qué piloto dominó cada década?**
3. **¿Qué piloto ganó más en cada año?**

#### 🥇 Victorias y Poles
4. **¿Qué piloto tiene más victorias?**
5. **¿Qué piloto tiene más pole positions?**
6. **¿Qué piloto ganó más en cada circuito?**
7. **¿Qué porcentaje de ganadores ganaron desde la pole position?**
8. **¿Qué piloto tiene la mejor conversión de poles en victorias?**

#### 🏁 Rendimiento de Equipos
9. **¿Qué equipo tiene mejor relación carreras disputadas/puntos obtenidos?**
10. **¿Qué equipo tiene la mayor cantidad de 1-2?** (primer y segundo lugar)
11. **¿Qué equipo ganó más en cada circuito?**

#### 📈 Evolución y Tendencias
12. **¿Cómo evolucionó el tiempo de pit stop a lo largo de los años?**
13. **¿Cómo evolucionó la posición final de un piloto a lo largo del año? ¿Y su posición de largada?**

#### 🎯 Análisis Específicos
14. **¿Cuántas victorias se dieron largando desde fuera del top 10?**

---

## 🎯 Indicadores Necesarios

De las preguntas anteriores, identificamos los siguientes **indicadores/métricas**:

### Métricas Principales
- Cantidad de victorias
- Cantidad de pole positions
- Cantidad de campeonatos
- Puntos totales
- Cantidad de carreras disputadas
- Posición final
- Posición de largada (grid)
- Tiempo de pit stop
- Cantidad de 1-2 (podios dobles)

### Métricas Derivadas
- Porcentaje victorias desde pole
- Ratio puntos/carreras
- Conversión poles → victorias
- Victorias desde fuera del top 10

---

## 🎯 FASE 2: MODELO DIMENSIONAL

### Modelo Conceptual - Esquema Estrella ⭐

```
                     Carrera
                        |
                        |
        Piloto ─────────┼───────── Tiempo final (ms)
                        |
                        |          Puntos obtenidos
     Constructor ───► RESULTADO ─► Posicion Final
                     DE CARRERA
                        |          Posicion de salida (Grid)
      Circuito ─────────┼───────── Vueltas completadas
                        |
                        |
                 Tiempo/Fecha
```

### Tabla de Hechos

**FACT: Resultado de Carrera**

Contiene las métricas de cada participación de un piloto en una carrera.

**Métricas (Hechos)**:
- Puntos obtenidos
- Posición final
- Posición de salida (Grid)
- Vueltas completadas
- Tiempo final (ms)

**Claves Foráneas (Dimensiones)**:
- id_piloto → dim_piloto
- id_constructor → dim_constructor
- id_circuito → dim_circuito
- id_carrera → dim_carrera
- id_tiempo → dim_tiempo

---

### Dimensiones (5 tablas)

#### 1️⃣ DIM_PILOTO
Información de los pilotos

**Atributos**:
- id_piloto (PK)
- nombre
- apellido
- nacionalidad
- fecha_nacimiento
- código (ej: HAM, VER, ALO)

**Fuente**: `drivers.csv`

---

#### 2️⃣ DIM_CONSTRUCTOR
Información de los equipos/escuderías

**Atributos**:
- id_constructor (PK)
- nombre
- nacionalidad
- año_fundacion

**Fuente**: `constructors.csv`

---

#### 3️⃣ DIM_CIRCUITO
Información de los circuitos

**Atributos**:
- id_circuito (PK)
- nombre_circuito
- ubicacion (ciudad)
- pais
- latitud
- longitud

**Fuente**: `circuits.csv`

---

#### 4️⃣ DIM_CARRERA
Información de cada Gran Premio

**Atributos**:
- id_carrera (PK)
- nombre_gp
- año
- ronda
- id_circuito (FK)

**Fuente**: `races.csv`

---

#### 5️⃣ DIM_TIEMPO
Dimensión temporal (fecha de la carrera)

**Atributos**:
- id_tiempo (PK)
- fecha
- año
- mes
- dia
- trimestre
- decada
- dia_semana

**Fuente**: Derivada de `races.csv` (columna date)

---

## 📐 Granularidad

**Un registro en la tabla de hechos representa:**
- Un piloto
- En una carrera específica
- Con un constructor/equipo
- En un circuito determinado
- En una fecha concreta

---

## �️ FASE 3: MODELO LÓGICO DEL DATA WAREHOUSE

### 1. Tipo de Modelo Lógico

**Modelo Seleccionado: ESQUEMA ESTRELLA (Star Schema)**

**Justificación:**
- ✅ **Simplicidad**: Fácil de entender y consultar
- ✅ **Performance**: Joins directos entre hechos y dimensiones
- ✅ **Desnormalizado**: Las dimensiones contienen información redundante para optimizar consultas
- ✅ **Ideal para BI**: Consultas analíticas rápidas con agregaciones
- ✅ **Recomendado por Hefesto**: Para análisis OLAP y reporting

**Características:**
- 1 tabla de hechos central (fact_resultado_carrera)
- 5 tablas de dimensiones desnormalizadas
- Relaciones directas mediante claves foráneas
- Sin jerarquías anidadas (no es copo de nieve)

---

### 2. Tablas de Dimensiones (5)

#### 📋 DIM_PILOTO

```sql
dim_piloto (
    piloto_id        INT PRIMARY KEY,
    nombre           VARCHAR(100),
    apellido         VARCHAR(100),
    nombre_completo  VARCHAR(200),
    codigo           VARCHAR(3),      -- HAM, VER, ALO
    numero           INT,              -- Número del piloto
    nacionalidad     VARCHAR(50),
    fecha_nacimiento DATE,
    url              TEXT
)
```

**Registros estimados:** ~860  
**Fuente:** `drivers.csv`  
**Clave primaria:** piloto_id (driverId en CSV)

---

#### 🏗️ DIM_CONSTRUCTOR

```sql
dim_constructor (
    constructor_id   INT PRIMARY KEY,
    nombre           VARCHAR(100),
    referencia       VARCHAR(50),
    nacionalidad     VARCHAR(50),
    url              TEXT
)
```

**Registros estimados:** ~212  
**Fuente:** `constructors.csv`  
**Clave primaria:** constructor_id (constructorId en CSV)

---

#### 🏁 DIM_CIRCUITO

```sql
dim_circuito (
    circuito_id      INT PRIMARY KEY,
    nombre           VARCHAR(100),
    ubicacion        VARCHAR(100),    -- Ciudad
    pais             VARCHAR(50),
    latitud          DECIMAL(10,6),
    longitud         DECIMAL(10,6),
    altitud          INT,
    url              TEXT
)
```

**Registros estimados:** ~77  
**Fuente:** `circuits.csv`  
**Clave primaria:** circuito_id (circuitId en CSV)

---

#### 🏆 DIM_CARRERA

```sql
dim_carrera (
    carrera_id       INT PRIMARY KEY,
    anio             INT,
    ronda            INT,
    circuito_id      INT,             -- FK a dim_circuito
    nombre_gp        VARCHAR(100),
    fecha            DATE,
    hora             TIME,
    url              TEXT,
    
    FOREIGN KEY (circuito_id) REFERENCES dim_circuito(circuito_id)
)
```

**Registros estimados:** ~1,100  
**Fuente:** `races.csv`  
**Clave primaria:** carrera_id (raceId en CSV)  
**FK:** circuito_id → dim_circuito

---

#### 📅 DIM_TIEMPO

```sql
dim_tiempo (
    tiempo_id        INT PRIMARY KEY,  -- YYYYMMDD formato
    fecha            DATE,
    anio             INT,
    mes              INT,
    dia              INT,
    trimestre        INT,              -- 1, 2, 3, 4
    decada           INT,              -- 1950, 1960, 1970...
    nombre_mes       VARCHAR(20),      -- Enero, Febrero...
    dia_semana       VARCHAR(20),      -- Lunes, Martes...
    es_fin_semana    BOOLEAN
)
```

**Registros estimados:** ~1,000 (fechas únicas)  
**Fuente:** Derivada de `races.csv` (columna date)  
**Clave primaria:** tiempo_id (formato YYYYMMDD, ej: 20240303)

---

### 3. Tabla de Hechos

#### 🎯 FACT_RESULTADO_CARRERA

```sql
fact_resultado_carrera (
    -- Claves Foráneas (Dimensiones)
    carrera_id           INT NOT NULL,
    piloto_id            INT NOT NULL,
    constructor_id       INT NOT NULL,
    circuito_id          INT NOT NULL,
    tiempo_id            INT NOT NULL,
    
    -- Métricas Numéricas
    puntos               DECIMAL(5,2),
    posicion_final       INT,
    posicion_salida      INT,          -- Grid position
    vueltas_completadas  INT,
    tiempo_final_ms      BIGINT,       -- Milisegundos
    
    -- Métricas Adicionales
    mejor_vuelta         INT,          -- Número de vuelta
    tiempo_mejor_vuelta  TIME,
    velocidad_promedio   DECIMAL(6,2),
    
    -- Métricas Derivadas (Calculadas)
    es_victoria          BOOLEAN,      -- posicion_final = 1
    es_podio             BOOLEAN,      -- posicion_final <= 3
    es_pole              BOOLEAN,      -- posicion_salida = 1
    es_punto             BOOLEAN,      -- puntos > 0
    completo_carrera     BOOLEAN,      -- Terminó la carrera
    
    -- Clave Primaria Compuesta
    PRIMARY KEY (carrera_id, piloto_id),
    
    -- Foreign Keys
    FOREIGN KEY (carrera_id) REFERENCES dim_carrera(carrera_id),
    FOREIGN KEY (piloto_id) REFERENCES dim_piloto(piloto_id),
    FOREIGN KEY (constructor_id) REFERENCES dim_constructor(constructor_id),
    FOREIGN KEY (circuito_id) REFERENCES dim_circuito(circuito_id),
    FOREIGN KEY (tiempo_id) REFERENCES dim_tiempo(tiempo_id)
)
```

**Registros estimados:** ~26,000  
**Fuente:** `results.csv` + joins con otras tablas  
**Granularidad:** Un registro = Un piloto en una carrera específica  
**Clave primaria:** (carrera_id, piloto_id)

---

### 4. Uniones (Joins)

#### Relaciones entre Tablas

```
fact_resultado_carrera.carrera_id → dim_carrera.carrera_id
fact_resultado_carrera.piloto_id → dim_piloto.piloto_id
fact_resultado_carrera.constructor_id → dim_constructor.constructor_id
fact_resultado_carrera.circuito_id → dim_circuito.circuito_id
fact_resultado_carrera.tiempo_id → dim_tiempo.tiempo_id

dim_carrera.circuito_id → dim_circuito.circuito_id (opcional)
```

#### Ejemplo de Consulta con Joins

```sql
-- P1: Top 10 pilotos con más victorias
SELECT 
    p.nombre_completo,
    p.nacionalidad,
    COUNT(*) as total_carreras,
    SUM(CASE WHEN f.es_victoria THEN 1 ELSE 0 END) as victorias,
    SUM(CASE WHEN f.es_podio THEN 1 ELSE 0 END) as podios,
    SUM(f.puntos) as puntos_totales
FROM fact_resultado_carrera f
INNER JOIN dim_piloto p ON f.piloto_id = p.piloto_id
GROUP BY p.piloto_id, p.nombre_completo, p.nacionalidad
ORDER BY victorias DESC, puntos_totales DESC
LIMIT 10;
```

```sql
-- P2: Evolución de un piloto por año
SELECT 
    t.anio,
    p.nombre_completo,
    COUNT(*) as carreras,
    SUM(f.puntos) as puntos,
    SUM(CASE WHEN f.es_victoria THEN 1 ELSE 0 END) as victorias,
    AVG(f.posicion_final) as promedio_posicion
FROM fact_resultado_carrera f
INNER JOIN dim_piloto p ON f.piloto_id = p.piloto_id
INNER JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
WHERE p.nombre_completo = 'Lewis Hamilton'
GROUP BY t.anio, p.nombre_completo
ORDER BY t.anio;
```

```sql
-- P7: Porcentaje de victorias desde pole position
SELECT 
    COUNT(CASE WHEN es_pole AND es_victoria THEN 1 END) * 100.0 / 
    COUNT(CASE WHEN es_victoria THEN 1 END) as porcentaje_pole_to_win
FROM fact_resultado_carrera;
```

#### Tipos de Join Utilizados

1. **INNER JOIN**: Para relaciones obligatorias (todos los registros tienen dimensiones)
2. **LEFT JOIN**: Para dimensiones opcionales (si las hubiera)
3. **No se usan OUTER JOINS**: El modelo estrella garantiza integridad referencial

---

## �📁 Datos Disponibles

- 14 archivos CSV
- Período: 1950-2024 (75 temporadas)
- ~700,000 registros totales

---

## 🚀 Próximos Pasos

1. ✅ Identificar preguntas de negocio (COMPLETADO)
2. ✅ Extraer indicadores y perspectivas (COMPLETADO)
3. ✅ Diseñar modelo dimensional - Esquema Estrella (COMPLETADO)
4. ✅ Definir modelo lógico del DW (COMPLETADO)
5. ✅ Crear DDL de base de datos SQL (COMPLETADO)
6. ⏳ Implementar proceso ETL
7. ⏳ Responder preguntas con consultas SQL

---

## 🔄 FASE 4: PROCESO ETL (Extract, Transform, Load)

### Objetivo

Implementar un proceso ETL para la **carga inicial** de los 14 archivos CSV del histórico de F1 (1950-2024) en el esquema estrella, asegurando integridad referencial y calidad de datos.

### Metodología Hefesto - Orden de Carga

**CRÍTICO**: Seguir el orden estricto para satisfacer dependencias de FK:

```
1. dim_piloto         (sin dependencias)
2. dim_constructor    (sin dependencias)
3. dim_circuito       (sin dependencias)
4. dim_tiempo         (sin dependencias)
5. dim_carrera        (depende de dim_circuito)
6. fact_resultado     (depende de TODAS las dimensiones)
```

---

### A. Lineamientos Generales

1. **Documentación Detallada**: Cada paso del ETL explicado
2. **Calidad de Datos**: Limpieza de valores nulos/anómalos
3. **Fuentes**: 14 archivos CSV (drivers.csv, constructors.csv, etc.)
4. **Granularidad**: Un registro = Un piloto en una carrera específica

---

### B. Carga de Dimensiones (Paso a Paso)

#### 1️⃣ DIM_PILOTO

**Fuente**: `drivers.csv`

**Pasos**:
1. Extraer: Leer drivers.csv
2. Transformar:
   - Concatenar `nombre_completo = forename + " " + surname`
   - Limpiar valores nulos en campos críticos
3. Cargar: INSERT INTO dim_piloto

**Mapeo de Columnas**:
```
CSV → Base de Datos
--------------------------------
driverId → piloto_id (PK)
forename → nombre
surname → apellido
forename + surname → nombre_completo
code → codigo
number → numero
nationality → nacionalidad
dob → fecha_nacimiento
url → url
```

**Registros Esperados**: ~860

---

#### 2️⃣ DIM_CONSTRUCTOR

**Fuente**: `constructors.csv`

**Pasos**:
1. Extraer: Leer constructors.csv
2. Transformar: Mapeo directo (sin transformaciones complejas)
3. Cargar: INSERT INTO dim_constructor

**Mapeo de Columnas**:
```
CSV → Base de Datos
--------------------------------
constructorId → constructor_id (PK)
name → nombre
constructorRef → referencia
nationality → nacionalidad
url → url
```

**Registros Esperados**: ~212

---

#### 3️⃣ DIM_CIRCUITO

**Fuente**: `circuits.csv`

**Pasos**:
1. Extraer: Leer circuits.csv
2. Transformar: 
   - Convertir lat/lng a DECIMAL
   - Limpiar valores nulos
3. Cargar: INSERT INTO dim_circuito

**Mapeo de Columnas**:
```
CSV → Base de Datos
--------------------------------
circuitId → circuito_id (PK)
name → nombre
location → ubicacion
country → pais
lat → latitud
lng → longitud
alt → altitud
url → url
```

**Registros Esperados**: ~77

---

#### 4️⃣ DIM_TIEMPO

**Fuente**: Derivada de `races.csv` (columna `date`)

**Pasos**:
1. Extraer: Leer fechas únicas de races.csv
2. Transformar (GENERACIÓN DIMENSIONAL):
   ```python
   tiempo_id = YYYYMMDD (ej: 20240303)
   anio = EXTRACT(YEAR FROM fecha)
   mes = EXTRACT(MONTH FROM fecha)
   dia = EXTRACT(DAY FROM fecha)
   trimestre = CEIL(mes / 3)
   decada = FLOOR(anio / 10) * 10
   nombre_mes = ['Enero', 'Febrero', ...]
   dia_semana = ['Lunes', 'Martes', ...]
   es_fin_semana = (dia_semana IN ['Sábado', 'Domingo'])
   ```
3. Cargar: INSERT INTO dim_tiempo

**Clave**: `tiempo_id` debe ser numérico formato YYYYMMDD

**Registros Esperados**: ~1,000 (fechas únicas)

---

#### 5️⃣ DIM_CARRERA

**Fuente**: `races.csv`

**Dependencia**: ⚠️ Requiere que `dim_circuito` esté cargada (FK)

**Pasos**:
1. Extraer: Leer races.csv
2. Transformar:
   - Validar que `circuitId` existe en dim_circuito
   - Convertir fecha/hora a tipos correctos
3. Cargar: INSERT INTO dim_carrera

**Mapeo de Columnas**:
```
CSV → Base de Datos
--------------------------------
raceId → carrera_id (PK)
year → anio
round → ronda
circuitId → circuito_id (FK)
name → nombre_gp
date → fecha
time → hora
url → url
```

**Validación Crítica**: 
```sql
-- Verificar integridad referencial
SELECT COUNT(*) FROM races r
LEFT JOIN dim_circuito c ON r.circuitId = c.circuito_id
WHERE c.circuito_id IS NULL;
-- Debe retornar 0
```

**Registros Esperados**: ~1,100

---

### C. Carga de Tabla de Hechos

#### 🎯 FACT_RESULTADO_CARRERA

**Fuente Principal**: `results.csv`

**Dependencias**: ⚠️ Requiere las 5 dimensiones cargadas

**Pasos Detallados**:

##### 1. EXTRACCIÓN
```python
# Leer archivo fuente
results_df = pd.read_csv('results.csv')
```

##### 2. TRANSFORMACIÓN

###### 2.1 Lookups (Búsqueda de FKs)

```sql
-- Lookup 1: Obtener piloto_id
SELECT piloto_id FROM dim_piloto WHERE piloto_id = results.driverId

-- Lookup 2: Obtener constructor_id  
SELECT constructor_id FROM dim_constructor WHERE constructor_id = results.constructorId

-- Lookup 3: Obtener carrera_id
SELECT carrera_id FROM dim_carrera WHERE carrera_id = results.raceId

-- Lookup 4: Obtener circuito_id (a través de carrera)
SELECT circuito_id FROM dim_carrera WHERE carrera_id = results.raceId

-- Lookup 5: Obtener tiempo_id (a través de carrera)
SELECT c.fecha 
FROM dim_carrera c 
WHERE c.carrera_id = results.raceId
-- Luego convertir fecha a YYYYMMDD
```

###### 2.2 Cálculo de Métricas Derivadas

```python
# Métricas Booleanas
es_victoria = (posicion_final == 1)
es_podio = (posicion_final <= 3)
es_pole = (posicion_salida == 1)
es_punto = (puntos > 0)
completo_carrera = (statusId == 1)  # 1 = "Finished"
```

###### 2.3 Transformación de Tipos

```python
# Conversiones
puntos = DECIMAL(5,2)
posicion_final = INTEGER
posicion_salida = INTEGER  # grid
vueltas_completadas = INTEGER  # laps
tiempo_final_ms = BIGINT  # milliseconds
```

##### 3. CARGA

```sql
INSERT INTO fact_resultado_carrera (
    carrera_id,
    piloto_id,
    constructor_id,
    circuito_id,
    tiempo_id,
    puntos,
    posicion_final,
    posicion_salida,
    vueltas_completadas,
    tiempo_final_ms,
    mejor_vuelta,
    tiempo_mejor_vuelta,
    velocidad_promedio,
    es_victoria,
    es_podio,
    es_pole,
    es_punto,
    completo_carrera
) VALUES (...);
```

**Mapeo Completo CSV → Tabla**:
```
results.csv → fact_resultado_carrera
----------------------------------------
raceId → carrera_id (FK)
driverId → piloto_id (FK)
constructorId → constructor_id (FK)
(lookup via carrera) → circuito_id (FK)
(lookup via carrera) → tiempo_id (FK)

points → puntos
position → posicion_final
grid → posicion_salida
laps → vueltas_completadas
milliseconds → tiempo_final_ms
fastestLap → mejor_vuelta
fastestLapTime → tiempo_mejor_vuelta
fastestLapSpeed → velocidad_promedio

(calculado) → es_victoria
(calculado) → es_podio
(calculado) → es_pole
(calculado) → es_punto
statusId == 1 → completo_carrera
```

**Registros Esperados**: ~26,000

---

### D. Verificación de Integridad

#### 1. Validación de Conteo

```sql
-- Verificar dimensiones
SELECT 'dim_piloto' as tabla, COUNT(*) as registros FROM dim_piloto
UNION ALL
SELECT 'dim_constructor', COUNT(*) FROM dim_constructor
UNION ALL
SELECT 'dim_circuito', COUNT(*) FROM dim_circuito
UNION ALL
SELECT 'dim_tiempo', COUNT(*) FROM dim_tiempo
UNION ALL
SELECT 'dim_carrera', COUNT(*) FROM dim_carrera
UNION ALL
SELECT 'fact_resultado_carrera', COUNT(*) FROM fact_resultado_carrera;
```

**Resultados Esperados**:
- dim_piloto: ~860
- dim_constructor: ~212
- dim_circuito: ~77
- dim_tiempo: ~1,000
- dim_carrera: ~1,100
- fact_resultado_carrera: ~26,000

#### 2. Integridad Referencial

```sql
-- Verificar que NO existan registros huérfanos

-- Check 1: Pilotos huérfanos
SELECT COUNT(*) 
FROM fact_resultado_carrera f
LEFT JOIN dim_piloto p ON f.piloto_id = p.piloto_id
WHERE p.piloto_id IS NULL;
-- Debe retornar: 0

-- Check 2: Constructores huérfanos
SELECT COUNT(*) 
FROM fact_resultado_carrera f
LEFT JOIN dim_constructor c ON f.constructor_id = c.constructor_id
WHERE c.constructor_id IS NULL;
-- Debe retornar: 0

-- Check 3: Circuitos huérfanos
SELECT COUNT(*) 
FROM fact_resultado_carrera f
LEFT JOIN dim_circuito c ON f.circuito_id = c.circuito_id
WHERE c.circuito_id IS NULL;
-- Debe retornar: 0

-- Check 4: Carreras huérfanas
SELECT COUNT(*) 
FROM fact_resultado_carrera f
LEFT JOIN dim_carrera c ON f.carrera_id = c.carrera_id
WHERE c.carrera_id IS NULL;
-- Debe retornar: 0

-- Check 5: Tiempos huérfanos
SELECT COUNT(*) 
FROM fact_resultado_carrera f
LEFT JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
WHERE t.tiempo_id IS NULL;
-- Debe retornar: 0
```

#### 3. Calidad de Datos

```sql
-- Verificar métricas derivadas
SELECT 
    COUNT(*) as total_registros,
    SUM(CASE WHEN es_victoria THEN 1 ELSE 0 END) as victorias,
    SUM(CASE WHEN es_podio THEN 1 ELSE 0 END) as podios,
    SUM(CASE WHEN es_pole THEN 1 ELSE 0 END) as poles,
    SUM(CASE WHEN es_punto THEN 1 ELSE 0 END) as puntos_positivos
FROM fact_resultado_carrera;

-- Verificar coherencia: todas las victorias deben ser podios
SELECT COUNT(*) 
FROM fact_resultado_carrera 
WHERE es_victoria = TRUE AND es_podio = FALSE;
-- Debe retornar: 0
```

---

## 📊 Resumen del Proceso ETL

```
ORDEN DE EJECUCIÓN:
1. dim_piloto         ✅ 860 registros
2. dim_constructor    ✅ 212 registros
3. dim_circuito       ✅ 77 registros
4. dim_tiempo         ✅ 1,000 registros (generados)
5. dim_carrera        ✅ 1,100 registros (FK → circuito)
6. fact_resultado     ✅ 26,000 registros (FK → todas)

VALIDACIONES:
✓ Conteo de registros
✓ Integridad referencial (0 huérfanos)
✓ Coherencia de métricas derivadas
```

---

**Metodología**: Hefesto (Bernabeu, 2010)  
**Autor**: Mateo Pappalardo  
**Curso**: Base de Datos II
