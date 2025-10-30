# Datos Fuente - F1 Data Warehouse 📊

## Descripción

Esta carpeta contiene los **archivos CSV fuente** con datos históricos de Fórmula 1 desde 1950 hasta 2024. Estos archivos son el origen de datos (OLTP) que se procesan mediante el ETL para construir el Data Warehouse (OLAP).

---

## 📁 Archivos CSV

### Dimensiones Principales

| Archivo | Registros | Descripción |
|---------|-----------|-------------|
| `drivers.csv` | 861 | Información de pilotos (nombre, nacionalidad, fecha nacimiento) |
| `constructors.csv` | 212 | Equipos/Constructores (nombre, nacionalidad) |
| `circuits.csv` | 77 | Circuitos (nombre, ubicación, coordenadas GPS) |
| `status.csv` | 139 | Estados de finalización (Finished, Accident, Engine, etc.) |
| `seasons.csv` | 75 | Temporadas (1950-2024) |

### Datos de Carreras

| Archivo | Registros | Descripción |
|---------|-----------|-------------|
| `races.csv` | 1,125 | Información de Grandes Premios (fecha, circuito, año) |
| `results.csv` | 26,759 | Resultados de carreras (posición, puntos, tiempo) |
| `qualifying.csv` | 10,494 | Resultados de clasificación (Q1, Q2, Q3) |
| `sprint_results.csv` | 360 | Resultados de carreras sprint (2021+) |

### Datos Detallados

| Archivo | Registros | Descripción |
|---------|-----------|-------------|
| `lap_times.csv` | 589,081 | Tiempos de vuelta detallados |
| `pit_stops.csv` | 11,371 | Paradas en boxes (duración, vuelta) |
| `driver_standings.csv` | 34,863 | Clasificación de pilotos por carrera |
| `constructor_standings.csv` | 13,391 | Clasificación de constructores por carrera |
| `constructor_results.csv` | 12,625 | Resultados agregados por constructor |

---

## 📊 Estadísticas Generales

- **Total de archivos**: 14 CSV
- **Total de registros**: ~701,433 filas
- **Período cubierto**: 1950 - 2024 (75 temporadas)
- **Tamaño aproximado**: ~150 MB
- **Formato**: CSV con separador `,`
- **Encoding**: UTF-8
- **Valores nulos**: Representados como `\N`

---

## 🔄 Uso en el ETL

Estos archivos son leídos por el proceso ETL en la **fase de extracción**:

```python
# Extract (etl/extract/extractor.py)
data = pd.read_csv('data/drivers.csv', na_values=['\\N'])
```

### Mapeo a Dimensiones

| CSV Fuente | Tabla Destino DW | Tipo |
|------------|------------------|------|
| `drivers.csv` | `dim_piloto` | Dimensión |
| `constructors.csv` | `dim_constructor` | Dimensión |
| `circuits.csv` | `dim_circuito` | Dimensión |
| `status.csv` | `dim_status` | Dimensión |
| `races.csv` | `dim_carrera` + `dim_tiempo` | Dimensión |
| `results.csv` + `races.csv` | `fact_resultados_carrera` | Hecho |

---

## 📝 Formato de Datos

### Ejemplo: drivers.csv
```csv
driverId,driverRef,number,code,forename,surname,dob,nationality,url
1,hamilton,44,HAM,Lewis,Hamilton,1985-01-07,British,http://en.wikipedia.org/wiki/Lewis_Hamilton
2,alonso,14,ALO,Fernando,Alonso,1981-07-29,Spanish,http://en.wikipedia.org/wiki/Fernando_Alonso
```

### Ejemplo: results.csv
```csv
resultId,raceId,driverId,constructorId,number,grid,position,positionText,points,laps,time,milliseconds,fastestLap,rank,fastestLapTime,fastestLapSpeed,statusId
1,18,1,1,22,1,1,1,10.0,58,1:34:50.616,5690616,39,2,1:27.452,218.300,1
```

### Valores Especiales

- **`\N`**: Representa valores nulos o no disponibles
- **Posiciones**: Números enteros (1 = primero, 2 = segundo, etc.)
- **Tiempos**: En formato `mm:ss.sss` o milisegundos
- **Fechas**: Formato ISO `YYYY-MM-DD`

---

## 🔍 Análisis Exploratorio

Para analizar estos archivos antes de cargarlos al DW:

```bash
# Ejecutar script de análisis
python3 describe_tables.py
```

Este script proporciona:
- Conteo de filas y columnas
- Tipos de datos
- Valores nulos
- Estadísticas descriptivas
- Muestras de datos

---

## 📚 Fuente de Datos

**Dataset**: Ergast Developer API  
**URL**: http://ergast.com/mrd/  
**Licencia**: Creative Commons Attribution-NonCommercial  
**Última actualización**: 2024  
**Mantenedor**: Ergast Motor Racing Database  

### Cómo actualizar los datos

1. Descargar nuevos CSVs desde Ergast API
2. Reemplazar archivos en esta carpeta
3. Ejecutar ETL completo: `python3 etl/run_etl_hefesto.py`

---

## ⚠️ Notas Importantes

1. **No modificar manualmente**: Estos archivos son la fuente de verdad (OLTP)
2. **Backup recomendado**: Mantener copia de los CSVs originales
3. **Integridad**: Relaciones entre CSVs mediante IDs (driverId, raceId, etc.)
4. **Calidad**: Algunos datos históricos pueden ser incompletos (pre-1980)
5. **Consistencia**: Respetar formato CSV original para el ETL

---

## 🚀 Próximos Pasos

1. ✅ Analizar datos con `describe_tables.py`
2. ✅ Configurar base de datos PostgreSQL
3. ✅ Ejecutar ETL: `python3 etl/run_etl_hefesto.py`
4. ✅ Validar datos en el Data Warehouse
5. ✅ Crear consultas analíticas

---

**Ver también:**
- [`readme.md`](../readme.md) - Documentación principal
- [`etl/README_ETL.md`](../etl/README_ETL.md) - Detalles del ETL
- [`METODOLOGIA_HEFESTO.md`](../METODOLOGIA_HEFESTO.md) - Metodología aplicada
