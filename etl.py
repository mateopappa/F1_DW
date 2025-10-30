"""
F1 Data Warehouse - Proceso ETL
Metodología: Hefesto
Orden: Dimensiones → Tabla de Hechos
Base de Datos: MySQL
"""

import pandas as pd
import mysql.connector
from datetime import datetime
import os

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'database': 'f1_datawarehouse',
    'user': 'root',  
    'password': ''   
}

DATA_DIR = 'data'

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_connection():
    """Obtener conexión a MySQL"""
    return mysql.connector.connect(**DB_CONFIG)

def read_csv_safe(filename):
    """Leer CSV con manejo de valores nulos"""
    filepath = os.path.join(DATA_DIR, filename)
    return pd.read_csv(filepath, na_values=['\\N', 'N/A', ''])

def execute_sql_file(conn, filepath):
    """Ejecutar archivo SQL (MySQL requiere ejecutar múltiples statements)"""
    cursor = conn.cursor()
    with open(filepath, 'r') as f:
        # Leer contenido completo
        sql_script = f.read()
        
        # Ejecutar cada statement individualmente
        for statement in sql_script.split(';'):
            statement = statement.strip()
            if statement:  # Ignorar statements vacíos
                cursor.execute(statement)
    
    cursor.close()

# ============================================================================
# PASO 1: CREAR ESQUEMA (Ejecutar DDL)
# ============================================================================

def crear_esquema():
    """Crear todas las tablas del DW"""
    print("=" * 80)
    print("PASO 1: CREANDO ESQUEMA DE BASE DE DATOS")
    print("=" * 80)
    
    conn = get_connection()
    
    try:
        execute_sql_file(conn, 'sql/create_tables.sql')
        conn.commit()
        print("✅ Esquema creado exitosamente\n")
    except Exception as e:
        print(f"❌ Error al crear esquema: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

# ============================================================================
# PASO 2: CARGAR DIMENSIONES (Orden Hefesto)
# ============================================================================

def cargar_dim_piloto():
    """
    1️⃣ DIMENSIÓN: PILOTO
    Fuente: drivers.csv
    Transformación: Concatenar nombre completo
    """
    print("-" * 80)
    print("1️⃣  Cargando DIM_PILOTO...")
    print("-" * 80)
    
    # EXTRACT
    df = read_csv_safe('drivers.csv')
    print(f"📥 Extraídos: {len(df)} registros")
    
    # TRANSFORM
    df['nombre_completo'] = df['forename'] + ' ' + df['surname']
    
    # Seleccionar y renombrar columnas
    df_clean = df[[
        'driverId', 'forename', 'surname', 'code', 
        'number', 'nationality', 'dob', 'url'
    ]].copy()
    
    df_clean['nombre_completo'] = df['nombre_completo']
    
    # Renombrar para coincidir con BD
    df_clean.columns = [
        'piloto_id', 'nombre', 'apellido', 'codigo',
        'numero', 'nacionalidad', 'fecha_nacimiento', 'url', 'nombre_completo'
    ]
    
    # CRÍTICO: Reordenar columnas para que coincidan EXACTAMENTE con el INSERT
    columnas_sql = [
        'piloto_id', 'nombre', 'apellido', 'nombre_completo', 'codigo',
        'numero', 'nacionalidad', 'fecha_nacimiento', 'url'
    ]
    df_clean = df_clean[columnas_sql]
    
    # Limpiar nulos críticos
    df_clean = df_clean.dropna(subset=['piloto_id'])
    
    # Reemplazar NaN con None (NULL en SQL)
    df_clean = df_clean.where(pd.notna(df_clean), None)
    
    print(f"🔄 Transformados: {len(df_clean)} registros")
    
    # LOAD
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for idx, row in df_clean.iterrows():
            # Convertir row a lista y reemplazar cualquier NaN/nan residual con None
            valores = []
            for val in row:
                if pd.isna(val):
                    valores.append(None)
                elif isinstance(val, float) and str(val).lower() == 'nan':
                    valores.append(None)
                else:
                    valores.append(val)
            
            cursor.execute("""
                INSERT IGNORE INTO dim_piloto (
                    piloto_id, nombre, apellido, nombre_completo, codigo,
                    numero, nacionalidad, fecha_nacimiento, url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(valores))
        
        conn.commit()
        print(f"✅ Cargados: {len(df_clean)} pilotos\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def cargar_dim_constructor():
    """
    2️⃣ DIMENSIÓN: CONSTRUCTOR
    Fuente: constructors.csv
    Transformación: Mapeo directo
    """
    print("-" * 80)
    print("2️⃣  Cargando DIM_CONSTRUCTOR...")
    print("-" * 80)
    
    # EXTRACT
    df = read_csv_safe('constructors.csv')
    print(f"📥 Extraídos: {len(df)} registros")
    
    # TRANSFORM
    df_clean = df[['constructorId', 'name', 'constructorRef', 'nationality', 'url']].copy()
    df_clean.columns = ['constructor_id', 'nombre', 'referencia', 'nacionalidad', 'url']
    df_clean = df_clean.dropna(subset=['constructor_id'])
    
    # Reemplazar NaN con None (NULL en SQL)
    df_clean = df_clean.where(pd.notna(df_clean), None)
    
    print(f"🔄 Transformados: {len(df_clean)} registros")
    
    # LOAD
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for _, row in df_clean.iterrows():
            # Convertir row a lista y reemplazar cualquier NaN residual con None
            valores = [None if pd.isna(val) else val for val in row]
            
            cursor.execute("""
                INSERT IGNORE INTO dim_constructor (
                    constructor_id, nombre, referencia, nacionalidad, url
                ) VALUES (%s, %s, %s, %s, %s)
            """, tuple(valores))
        
        conn.commit()
        print(f"✅ Cargados: {len(df_clean)} constructores\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def cargar_dim_circuito():
    """
    3️⃣ DIMENSIÓN: CIRCUITO
    Fuente: circuits.csv
    Transformación: Conversión de coordenadas
    """
    print("-" * 80)
    print("3️⃣  Cargando DIM_CIRCUITO...")
    print("-" * 80)
    
    # EXTRACT
    df = read_csv_safe('circuits.csv')
    print(f"📥 Extraídos: {len(df)} registros")
    
    # TRANSFORM
    df_clean = df[['circuitId', 'name', 'location', 'country', 'lat', 'lng', 'alt', 'url']].copy()
    df_clean.columns = ['circuito_id', 'nombre', 'ubicacion', 'pais', 'latitud', 'longitud', 'altitud', 'url']
    df_clean = df_clean.dropna(subset=['circuito_id'])
    
    # Reemplazar NaN con None (NULL en SQL)
    df_clean = df_clean.where(pd.notna(df_clean), None)
    
    print(f"🔄 Transformados: {len(df_clean)} registros")
    
    # LOAD
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for _, row in df_clean.iterrows():
            # Convertir row a lista y reemplazar cualquier NaN residual con None
            valores = [None if pd.isna(val) else val for val in row]
            
            cursor.execute("""
                INSERT IGNORE INTO dim_circuito (
                    circuito_id, nombre, ubicacion, pais, latitud, longitud, altitud, url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(valores))
        
        conn.commit()
        print(f"✅ Cargados: {len(df_clean)} circuitos\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def cargar_dim_tiempo():
    """
    4️⃣ DIMENSIÓN: TIEMPO (GENERADA)
    Fuente: Derivada de races.csv
    Transformación: Generación dimensional completa
    """
    print("-" * 80)
    print("4️⃣  Cargando DIM_TIEMPO (Generación Dimensional)...")
    print("-" * 80)
    
    # EXTRACT - Obtener fechas únicas
    df_races = read_csv_safe('races.csv')
    fechas_unicas = pd.to_datetime(df_races['date']).dropna().unique()
    
    print(f"📥 Extraídas: {len(fechas_unicas)} fechas únicas")
    
    # TRANSFORM - Generar atributos jerárquicos
    dim_tiempo = []
    
    meses_es = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    dias_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    for fecha in fechas_unicas:
        fecha_dt = pd.Timestamp(fecha)
        
        # Generar tiempo_id en formato YYYYMMDD
        tiempo_id = int(fecha_dt.strftime('%Y%m%d'))
        
        # Calcular atributos
        anio = fecha_dt.year
        mes = fecha_dt.month
        dia = fecha_dt.day
        trimestre = (mes - 1) // 3 + 1
        decada = (anio // 10) * 10
        nombre_mes = meses_es[mes]
        dia_semana = dias_es[fecha_dt.dayofweek]
        es_fin_semana = fecha_dt.dayofweek >= 5  # Sábado=5, Domingo=6
        
        dim_tiempo.append({
            'tiempo_id': tiempo_id,
            'fecha': fecha_dt.date(),
            'anio': anio,
            'mes': mes,
            'dia': dia,
            'trimestre': trimestre,
            'decada': decada,
            'nombre_mes': nombre_mes,
            'dia_semana': dia_semana,
            'es_fin_semana': es_fin_semana
        })
    
    df_tiempo = pd.DataFrame(dim_tiempo)
    print(f"🔄 Generados: {len(df_tiempo)} registros temporales")
    
    # LOAD
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for _, row in df_tiempo.iterrows():
            # Convertir boolean a int para MySQL (TINYINT)
            row_vals = list(row)
            row_vals[-1] = 1 if row_vals[-1] else 0  # es_fin_semana
            
            cursor.execute("""
                INSERT IGNORE INTO dim_tiempo (
                    tiempo_id, fecha, anio, mes, dia, trimestre, 
                    decada, nombre_mes, dia_semana, es_fin_semana
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(row_vals))
        
        conn.commit()
        print(f"✅ Cargados: {len(df_tiempo)} tiempos\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def cargar_dim_carrera():
    """
    5️⃣ DIMENSIÓN: CARRERA
    Fuente: races.csv
    Transformación: Validación de FK a circuito
    DEPENDENCIA: Requiere dim_circuito cargada
    """
    print("-" * 80)
    print("5️⃣  Cargando DIM_CARRERA...")
    print("-" * 80)
    
    # EXTRACT
    df = read_csv_safe('races.csv')
    print(f"📥 Extraídos: {len(df)} registros")
    
    # TRANSFORM
    df_clean = df[['raceId', 'year', 'round', 'circuitId', 'name', 'date', 'time', 'url']].copy()
    df_clean.columns = ['carrera_id', 'anio', 'ronda', 'circuito_id', 'nombre_gp', 'fecha', 'hora', 'url']
    
    # Limpiar registros sin circuito válido
    df_clean = df_clean.dropna(subset=['carrera_id', 'circuito_id'])
    
    # Reemplazar NaN con None (NULL en SQL)
    df_clean = df_clean.where(pd.notna(df_clean), None)
    
    print(f"🔄 Transformados: {len(df_clean)} registros")
    
    # LOAD
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        for _, row in df_clean.iterrows():
            # Convertir row a lista y reemplazar cualquier NaN residual con None
            valores = [None if pd.isna(val) else val for val in row]
            
            cursor.execute("""
                INSERT IGNORE INTO dim_carrera (
                    carrera_id, anio, ronda, circuito_id, nombre_gp, fecha, hora, url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, tuple(valores))
        
        conn.commit()
        print(f"✅ Cargados: {len(df_clean)} carreras\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# PASO 3: CARGAR TABLA DE HECHOS
# ============================================================================

def cargar_fact_resultado_carrera():
    """
    6️⃣ TABLA DE HECHOS: RESULTADO CARRERA
    Fuente: results.csv
    Transformación: Lookups + Métricas derivadas
    DEPENDENCIA: Requiere TODAS las dimensiones cargadas
    """
    print("=" * 80)
    print("6️⃣  Cargando FACT_RESULTADO_CARRERA...")
    print("=" * 80)
    
    # EXTRACT
    df_results = read_csv_safe('results.csv')
    df_races = read_csv_safe('races.csv')
    
    print(f"📥 Extraídos: {len(df_results)} resultados")
    
    # TRANSFORM - Merge con races para obtener fecha y circuito
    df = df_results.merge(df_races[['raceId', 'date', 'circuitId']], 
                          left_on='raceId', right_on='raceId', how='left')
    
    # Generar tiempo_id desde fecha
    df['fecha_dt'] = pd.to_datetime(df['date'])
    df['tiempo_id'] = df['fecha_dt'].apply(lambda x: int(x.strftime('%Y%m%d')) if pd.notna(x) else None)
    
    # Calcular métricas derivadas
    df['es_victoria'] = df['position'] == 1
    df['es_podio'] = df['position'] <= 3
    df['es_pole'] = df['grid'] == 1
    df['es_punto'] = df['points'] > 0
    df['completo_carrera'] = df['statusId'] == 1  # 1 = "Finished"
    
    # Seleccionar columnas finales
    df_fact = df[[
        'raceId', 'driverId', 'constructorId', 'circuitId', 'tiempo_id',
        'points', 'position', 'grid', 'laps', 'milliseconds',
        'fastestLap', 'fastestLapTime', 'fastestLapSpeed',
        'es_victoria', 'es_podio', 'es_pole', 'es_punto', 'completo_carrera'
    ]].copy()
    
    df_fact.columns = [
        'carrera_id', 'piloto_id', 'constructor_id', 'circuito_id', 'tiempo_id',
        'puntos', 'posicion_final', 'posicion_salida', 'vueltas_completadas', 'tiempo_final_ms',
        'mejor_vuelta', 'tiempo_mejor_vuelta', 'velocidad_promedio',
        'es_victoria', 'es_podio', 'es_pole', 'es_punto', 'completo_carrera'
    ]
    
    # Limpiar nulos críticos
    df_fact = df_fact.dropna(subset=['carrera_id', 'piloto_id', 'constructor_id', 'circuito_id', 'tiempo_id'])
    
    # Reemplazar NaN con None (NULL en SQL) ANTES de convertir booleanos
    df_fact = df_fact.where(pd.notna(df_fact), None)
    
    print(f"🔄 Transformados: {len(df_fact)} registros")
    
    # LOAD
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        registros_cargados = 0
        
        for _, row in df_fact.iterrows():
            try:
                # Convertir a lista y manejar NaN + booleanos
                row_vals = []
                for i, val in enumerate(row):
                    # Primero verificar si es NaN
                    if pd.isna(val):
                        row_vals.append(None)
                    # Convertir booleanos a int (columnas 13-17)
                    elif i >= 13 and i <= 17:
                        row_vals.append(1 if val else 0)
                    else:
                        row_vals.append(val)
                
                cursor.execute("""
                    INSERT IGNORE INTO fact_resultado_carrera (
                        carrera_id, piloto_id, constructor_id, circuito_id, tiempo_id,
                        puntos, posicion_final, posicion_salida, vueltas_completadas, tiempo_final_ms,
                        mejor_vuelta, tiempo_mejor_vuelta, velocidad_promedio,
                        es_victoria, es_podio, es_pole, es_punto, completo_carrera
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, tuple(row_vals))
                
                registros_cargados += 1
                
                # Commit cada 1000 registros
                if registros_cargados % 1000 == 0:
                    conn.commit()
                    print(f"  💾 Progreso: {registros_cargados} registros...")
            
            except Exception as e:
                print(f"  ⚠️  Error en registro: {e}")
                continue
        
        conn.commit()
        print(f"✅ Cargados: {registros_cargados} resultados de carrera\n")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# PASO 4: VERIFICACIÓN DE INTEGRIDAD
# ============================================================================

def verificar_integridad():
    """Verificar conteo y relaciones"""
    print("=" * 80)
    print("VERIFICACIÓN DE INTEGRIDAD")
    print("=" * 80)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Conteo de registros
        print("\n📊 Conteo de Registros:")
        print("-" * 80)
        
        tablas = [
            'dim_piloto',
            'dim_constructor',
            'dim_circuito',
            'dim_tiempo',
            'dim_carrera',
            'fact_resultado_carrera'
        ]
        
        for tabla in tablas:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cursor.fetchone()[0]
            print(f"  {tabla:30s}: {count:,} registros")
        
        # Verificar huérfanos
        print("\n🔍 Verificación de Integridad Referencial:")
        print("-" * 80)
        
        checks = [
            ("Pilotos huérfanos", """
                SELECT COUNT(*) FROM fact_resultado_carrera f
                LEFT JOIN dim_piloto p ON f.piloto_id = p.piloto_id
                WHERE p.piloto_id IS NULL
            """),
            ("Constructores huérfanos", """
                SELECT COUNT(*) FROM fact_resultado_carrera f
                LEFT JOIN dim_constructor c ON f.constructor_id = c.constructor_id
                WHERE c.constructor_id IS NULL
            """),
            ("Circuitos huérfanos", """
                SELECT COUNT(*) FROM fact_resultado_carrera f
                LEFT JOIN dim_circuito c ON f.circuito_id = c.circuito_id
                WHERE c.circuito_id IS NULL
            """),
            ("Carreras huérfanas", """
                SELECT COUNT(*) FROM fact_resultado_carrera f
                LEFT JOIN dim_carrera c ON f.carrera_id = c.carrera_id
                WHERE c.carrera_id IS NULL
            """),
            ("Tiempos huérfanos", """
                SELECT COUNT(*) FROM fact_resultado_carrera f
                LEFT JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
                WHERE t.tiempo_id IS NULL
            """)
        ]
        
        for nombre, query in checks:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            status = "✅" if count == 0 else "❌"
            print(f"  {status} {nombre:30s}: {count}")
        
        # Métricas
        print("\n📈 Métricas Derivadas:")
        print("-" * 80)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN es_victoria THEN 1 ELSE 0 END) as victorias,
                SUM(CASE WHEN es_podio THEN 1 ELSE 0 END) as podios,
                SUM(CASE WHEN es_pole THEN 1 ELSE 0 END) as poles
            FROM fact_resultado_carrera
        """)
        
        total, victorias, podios, poles = cursor.fetchone()
        print(f"  Total resultados: {total:,}")
        print(f"  Victorias: {victorias:,}")
        print(f"  Podios: {podios:,}")
        print(f"  Poles: {poles:,}")
        
        print("\n" + "=" * 80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 80)
    
    finally:
        cursor.close()
        conn.close()

# ============================================================================
# MAIN - EJECUTAR ETL COMPLETO
# ============================================================================

def main():
    """Ejecutar proceso ETL completo siguiendo metodología Hefesto"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "F1 DATA WAREHOUSE - PROCESO ETL" + " " * 26 + "║")
    print("║" + " " * 25 + "Metodología: Hefesto" + " " * 34 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    try:
        # Paso 1: Crear esquema
        crear_esquema()
        
        # Paso 2: Cargar dimensiones (ORDEN CRÍTICO)
        print("=" * 80)
        print("PASO 2: CARGANDO DIMENSIONES")
        print("=" * 80)
        print()
        
        cargar_dim_piloto()
        cargar_dim_constructor()
        cargar_dim_circuito()
        cargar_dim_tiempo()
        cargar_dim_carrera()
        
        # Paso 3: Cargar tabla de hechos
        print("=" * 80)
        print("PASO 3: CARGANDO TABLA DE HECHOS")
        print("=" * 80)
        print()
        
        cargar_fact_resultado_carrera()
        
        # Paso 4: Verificar
        verificar_integridad()
        
        print("\n🎉 ¡ETL COMPLETADO EXITOSAMENTE! 🎉\n")
    
    except Exception as e:
        print(f"\n❌ ERROR EN EL PROCESO ETL: {e}\n")
        raise

if __name__ == "__main__":
    main()
