"""
F1 Data Warehouse - Dashboard Interactivo
Metodología: Hefesto
Visualización: Streamlit + Plotly
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from datetime import datetime
import os

# ============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="F1 Data Warehouse",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

# Prioridad de configuración:
# 1. Variables de entorno (Docker/Railway)
# 2. Streamlit secrets (Streamlit Cloud)
# 3. Config local (desarrollo)

if os.getenv('MYSQL_HOST'):
    # Configuración desde variables de entorno (Docker/Railway/Producción)
    DB_CONFIG = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'database': os.getenv('MYSQL_DATABASE'),
        'user': os.getenv('MYSQL_USER'),
        'password': os.getenv('MYSQL_PASSWORD')
    }
else:
    try:
        # Si está en Streamlit Cloud (secrets.toml)
        DB_CONFIG = {
            'host': st.secrets["mysql"]["host"],
            'port': st.secrets["mysql"]["port"],
            'database': st.secrets["mysql"]["database"],
            'user': st.secrets["mysql"]["user"],
            'password': st.secrets["mysql"]["password"]
        }
    except (FileNotFoundError, KeyError):
        # Si está en local (desarrollo)
        DB_CONFIG = {
            'host': 'localhost',
            'port': 3306,
            'database': 'f1_datawarehouse',
            'user': 'root',
            'password': ''  # ⚠️ CAMBIA ESTO si tu MySQL tiene password
        }



# Crear connection string para SQLAlchemy
CONNECTION_STRING = f"mysql+mysqlconnector://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

# ============================================================================
# FUNCIONES DE CONEXIÓN
# ============================================================================

@st.cache_resource
def get_engine():
    """Obtener engine de SQLAlchemy (cacheado)"""
    return create_engine(CONNECTION_STRING)

@st.cache_data(ttl=600)  # Cache por 10 minutos
def ejecutar_query(query):
    """Ejecutar query y retornar DataFrame"""
    engine = get_engine()
    df = pd.read_sql(query, engine)
    return df

# ============================================================================
# QUERIES SQL (14 PREGUNTAS DE NEGOCIO)
# ============================================================================

def get_top_pilotos_victorias(limit=10):
    """¿Qué piloto tiene más victorias?"""
    query = f"""
        SELECT 
            p.nombre_completo,
            p.nacionalidad,
            COUNT(*) as victorias
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        WHERE f.es_victoria = 1
        GROUP BY p.piloto_id, p.nombre_completo, p.nacionalidad
        ORDER BY victorias DESC
        LIMIT {limit}
    """
    return ejecutar_query(query)

def get_top_pilotos_poles(limit=10):
    """¿Qué piloto tiene más pole positions?"""
    query = f"""
        SELECT 
            p.nombre_completo,
            p.nacionalidad,
            COUNT(*) as poles
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        WHERE f.es_pole = 1
        GROUP BY p.piloto_id, p.nombre_completo, p.nacionalidad
        ORDER BY poles DESC
        LIMIT {limit}
    """
    return ejecutar_query(query)

def get_victorias_por_decada():
    """¿Qué piloto dominó cada década?"""
    query = """
        SELECT 
            t.decada,
            p.nombre_completo,
            COUNT(*) as victorias
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE f.es_victoria = 1
        GROUP BY t.decada, p.piloto_id, p.nombre_completo
        ORDER BY t.decada, victorias DESC
    """
    return ejecutar_query(query)

def get_mejor_piloto_por_decada():
    """Top piloto por década"""
    df = get_victorias_por_decada()
    # Obtener el piloto con más victorias por década
    return df.loc[df.groupby('decada')['victorias'].idxmax()]

def get_constructores_performance():
    """¿Qué equipo tiene mejor relación carreras/puntos?"""
    query = """
        SELECT 
            c.nombre as constructor,
            COUNT(*) as carreras_disputadas,
            SUM(f.puntos) as puntos_totales,
            ROUND(SUM(f.puntos) / COUNT(*), 2) as puntos_por_carrera
        FROM fact_resultado_carrera f
        JOIN dim_constructor c ON f.constructor_id = c.constructor_id
        GROUP BY c.constructor_id, c.nombre
        HAVING carreras_disputadas > 100
        ORDER BY puntos_por_carrera DESC
        LIMIT 15
    """
    return ejecutar_query(query)

def get_victorias_fuera_top10():
    """¿Cuántas victorias se dieron largando desde fuera del top 10?"""
    query = """
        SELECT 
            COUNT(*) as victorias_fuera_top10,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_resultado_carrera WHERE es_victoria = 1), 2) as porcentaje
        FROM fact_resultado_carrera
        WHERE es_victoria = 1 AND posicion_salida > 10
    """
    return ejecutar_query(query)

def get_conversion_pole_victoria():
    """¿Qué porcentaje de ganadores ganaron desde la pole?"""
    query = """
        SELECT 
            COUNT(CASE WHEN es_pole = 1 AND es_victoria = 1 THEN 1 END) as poles_con_victoria,
            COUNT(CASE WHEN es_victoria = 1 THEN 1 END) as total_victorias,
            ROUND(COUNT(CASE WHEN es_pole = 1 AND es_victoria = 1 THEN 1 END) * 100.0 / 
                  COUNT(CASE WHEN es_victoria = 1 THEN 1 END), 2) as porcentaje_conversion
        FROM fact_resultado_carrera
    """
    return ejecutar_query(query)

def get_mejor_piloto_por_circuito():
    """¿Qué piloto ganó más en cada circuito?"""
    query = """
        WITH victorias_por_circuito AS (
            SELECT 
                circ.nombre AS circuito,
                p.nombre_completo AS piloto,
                COUNT(*) AS victorias,
                ROW_NUMBER() OVER (PARTITION BY circ.circuito_id ORDER BY COUNT(*) DESC) AS ranking
            FROM fact_resultado_carrera f
            JOIN dim_circuito circ ON f.circuito_id = circ.circuito_id
            JOIN dim_piloto p ON f.piloto_id = p.piloto_id
            WHERE f.es_victoria = 1
            GROUP BY circ.circuito_id, circ.nombre, p.piloto_id, p.nombre_completo
        )
        SELECT circuito, piloto, victorias
        FROM victorias_por_circuito
        WHERE ranking = 1
        ORDER BY victorias DESC
        LIMIT 20
    """
    return ejecutar_query(query)

def get_estadisticas_generales():
    """Estadísticas generales del DW"""
    query = """
        SELECT 
            COUNT(DISTINCT piloto_id) as total_pilotos,
            COUNT(DISTINCT constructor_id) as total_constructores,
            COUNT(DISTINCT circuito_id) as total_circuitos,
            COUNT(DISTINCT carrera_id) as total_carreras,
            COUNT(*) as total_resultados,
            SUM(es_victoria) as total_victorias,
            SUM(es_podio) as total_podios,
            SUM(es_pole) as total_poles
        FROM fact_resultado_carrera
    """
    return ejecutar_query(query)

def get_carreras_por_año():
    """Total de carreras disputadas por año"""
    query = """
        SELECT 
            t.anio,
            COUNT(DISTINCT f.carrera_id) as total_carreras
        FROM fact_resultado_carrera f
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        GROUP BY t.anio
        ORDER BY t.anio
    """
    return ejecutar_query(query)

def get_campeon_piloto_por_año(anio):
    """Obtener el campeón de pilotos de un año específico"""
    query = f"""
        SELECT 
            p.nombre_completo as campeon_piloto,
            SUM(f.puntos) as puntos_totales,
            SUM(f.es_victoria) as victorias
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE t.anio = {anio}
        GROUP BY p.piloto_id, p.nombre_completo
        ORDER BY puntos_totales DESC
        LIMIT 1
    """
    return ejecutar_query(query)

def get_campeon_constructor_por_año(anio):
    """Obtener el campeón de constructores de un año específico"""
    query = f"""
        SELECT 
            c.nombre as campeon_constructor,
            SUM(f.puntos) as puntos_totales,
            SUM(f.es_victoria) as victorias
        FROM fact_resultado_carrera f
        JOIN dim_constructor c ON f.constructor_id = c.constructor_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE t.anio = {anio}
        GROUP BY c.constructor_id, c.nombre
        ORDER BY puntos_totales DESC
        LIMIT 1
    """
    return ejecutar_query(query)

def get_estadisticas_año(anio):
    """Estadísticas completas de un año específico"""
    query = f"""
        SELECT 
            COUNT(DISTINCT f.carrera_id) as carreras,
            COUNT(DISTINCT f.piloto_id) as pilotos_participantes,
            COUNT(DISTINCT f.constructor_id) as constructores,
            COUNT(DISTINCT f.circuito_id) as circuitos_diferentes,
            MAX(f.puntos) as puntos_maximos_carrera
        FROM fact_resultado_carrera f
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE t.anio = {anio}
    """
    return ejecutar_query(query)

def get_evolucion_victorias_por_año():
    """Evolución de victorias por año"""
    query = """
        SELECT 
            t.anio,
            COUNT(*) as victorias
        FROM fact_resultado_carrera f
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE f.es_victoria = 1
        GROUP BY t.anio
        ORDER BY t.anio
    """
    return ejecutar_query(query)

# ============================================================================
# QUERIES PARA ANÁLISIS INTERACTIVO
# ============================================================================

def get_circuitos_por_continente(anios=None):
    """Distribución de circuitos por continente/región
    
    Args:
        anios: Lista de años para filtrar (None = todos los años)
    """
    if anios and len(anios) > 0:
        # Filtrar por años específicos usando carreras disputadas
        anios_str = ','.join(map(str, anios))
        query = f"""
            SELECT 
                CASE 
                    WHEN circ.pais IN ('UK', 'Spain', 'Italy', 'Monaco', 'France', 'Germany', 'Belgium', 
                                  'Netherlands', 'Austria', 'Portugal', 'Hungary', 'Russia', 'Turkey',
                                  'Sweden', 'Switzerland') THEN 'Europa'
                    WHEN circ.pais IN ('USA', 'Canada', 'Mexico', 'Brazil', 'Argentina') THEN 'América'
                    WHEN circ.pais IN ('Japan', 'China', 'Malaysia', 'Singapore', 'South Korea', 
                                  'India', 'Bahrain', 'UAE', 'Qatar', 'Saudi Arabia') THEN 'Asia'
                    WHEN circ.pais IN ('Australia', 'New Zealand') THEN 'Oceanía'
                    WHEN circ.pais IN ('South Africa', 'Morocco') THEN 'África'
                    ELSE 'Otros'
                END as continente,
                COUNT(DISTINCT circ.circuito_id) as cantidad_circuitos,
                COUNT(DISTINCT f.carrera_id) as carreras_disputadas,
                GROUP_CONCAT(DISTINCT circ.nombre ORDER BY circ.nombre SEPARATOR ', ') as circuitos
            FROM dim_circuito circ
            INNER JOIN fact_resultado_carrera f ON circ.circuito_id = f.circuito_id
            INNER JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
            WHERE t.anio IN ({anios_str})
            GROUP BY continente
            ORDER BY cantidad_circuitos DESC
        """
    else:
        # Vista global (todos los circuitos registrados)
        query = """
            SELECT 
                CASE 
                    WHEN pais IN ('UK', 'Spain', 'Italy', 'Monaco', 'France', 'Germany', 'Belgium', 
                                  'Netherlands', 'Austria', 'Portugal', 'Hungary', 'Russia', 'Turkey',
                                  'Sweden', 'Switzerland') THEN 'Europa'
                    WHEN pais IN ('USA', 'Canada', 'Mexico', 'Brazil', 'Argentina') THEN 'América'
                    WHEN pais IN ('Japan', 'China', 'Malaysia', 'Singapore', 'South Korea', 
                                  'India', 'Bahrain', 'UAE', 'Qatar', 'Saudi Arabia') THEN 'Asia'
                    WHEN pais IN ('Australia', 'New Zealand') THEN 'Oceanía'
                    WHEN pais IN ('South Africa', 'Morocco') THEN 'África'
                    ELSE 'Otros'
                END as continente,
                COUNT(*) as cantidad_circuitos,
                GROUP_CONCAT(DISTINCT nombre ORDER BY nombre SEPARATOR ', ') as circuitos
            FROM dim_circuito
            GROUP BY continente
            ORDER BY cantidad_circuitos DESC
        """
    return ejecutar_query(query)

def get_lista_constructores():
    """Obtener lista de constructores"""
    query = """
        SELECT DISTINCT nombre
        FROM dim_constructor
        ORDER BY nombre
    """
    return ejecutar_query(query)

def get_lista_constructores_activos_recientes():
    """Obtener constructores que participaron en los últimos 4 años consecutivos (2021-2024)
    Para análisis de tiempos de vuelta donde los datos están disponibles desde 2004
    """
    query = """
        WITH constructores_por_anio AS (
            SELECT DISTINCT 
                c.constructor_id,
                c.nombre,
                t.anio
            FROM fact_resultado_carrera f
            JOIN dim_constructor c ON f.constructor_id = c.constructor_id
            JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
            WHERE t.anio >= 2021 AND t.anio <= 2024
        ),
        constructores_con_4_anios AS (
            SELECT 
                constructor_id,
                nombre,
                COUNT(DISTINCT anio) as anios_participados
            FROM constructores_por_anio
            GROUP BY constructor_id, nombre
            HAVING COUNT(DISTINCT anio) = 4
        )
        SELECT nombre
        FROM constructores_con_4_anios
        ORDER BY nombre
    """
    return ejecutar_query(query)

def get_lista_circuitos():
    """Obtener lista de circuitos"""
    query = """
        SELECT DISTINCT nombre, pais
        FROM dim_circuito
        ORDER BY nombre
    """
    return ejecutar_query(query)

def get_evolucion_tiempos_constructor_circuito(constructor, circuito):
    """Evolución de mejor vuelta de un constructor vs promedio general en un circuito"""
    query = f"""
        WITH tiempos_constructor AS (
            -- Mejor tiempo del constructor seleccionado por año
            SELECT 
                t.anio,
                MIN(f.tiempo_mejor_vuelta / 1000.0 / 60.0) as mejor_vuelta_constructor
            FROM fact_resultado_carrera f
            JOIN dim_constructor c ON f.constructor_id = c.constructor_id
            JOIN dim_circuito circ ON f.circuito_id = circ.circuito_id
            JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
            WHERE c.nombre = '{constructor}'
              AND circ.nombre = '{circuito}'
              AND f.tiempo_mejor_vuelta IS NOT NULL
              AND f.tiempo_mejor_vuelta > 0
            GROUP BY t.anio
        ),
        tiempos_promedio_general AS (
            -- Mejor tiempo promedio de todos los constructores por año
            SELECT 
                t.anio,
                AVG(mejor_tiempo) as mejor_vuelta_promedio
            FROM (
                SELECT 
                    t.anio,
                    c.constructor_id,
                    MIN(f.tiempo_mejor_vuelta / 1000.0 / 60.0) as mejor_tiempo
                FROM fact_resultado_carrera f
                JOIN dim_constructor c ON f.constructor_id = c.constructor_id
                JOIN dim_circuito circ ON f.circuito_id = circ.circuito_id
                JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
                WHERE circ.nombre = '{circuito}'
                  AND f.tiempo_mejor_vuelta IS NOT NULL
                  AND f.tiempo_mejor_vuelta > 0
                GROUP BY t.anio, c.constructor_id
            ) AS mejores_por_constructor
            JOIN dim_tiempo t ON 1=1
            GROUP BY t.anio
        )
        SELECT 
            tc.anio,
            tc.mejor_vuelta_constructor,
            tpg.mejor_vuelta_promedio,
            (tc.mejor_vuelta_constructor - tpg.mejor_vuelta_promedio) as diferencia_vs_promedio,
            CASE 
                WHEN tc.mejor_vuelta_constructor < tpg.mejor_vuelta_promedio THEN 'Por debajo del promedio'
                WHEN tc.mejor_vuelta_constructor > tpg.mejor_vuelta_promedio THEN 'Por encima del promedio'
                ELSE 'En el promedio'
            END as rendimiento_relativo
        FROM tiempos_constructor tc
        LEFT JOIN tiempos_promedio_general tpg ON tc.anio = tpg.anio
        ORDER BY tc.anio
    """
    return ejecutar_query(query)

def get_pilotos_por_nacionalidad():
    """Distribución de pilotos por nacionalidad"""
    query = """
        SELECT 
            nacionalidad,
            COUNT(*) as cantidad_pilotos
        FROM dim_piloto
        GROUP BY nacionalidad
        ORDER BY cantidad_pilotos DESC
        LIMIT 15
    """
    return ejecutar_query(query)

def get_victorias_por_constructor_filtrado(constructor=None, decada=None):
    """Victorias filtradas por constructor y/o década"""
    where_clauses = ["f.es_victoria = 1"]
    
    if constructor:
        where_clauses.append(f"c.nombre = '{constructor}'")
    if decada:
        where_clauses.append(f"t.decada = {decada}")
    
    where_sql = " AND ".join(where_clauses)
    
    query = f"""
        SELECT 
            t.anio,
            COUNT(*) as victorias,
            GROUP_CONCAT(DISTINCT p.nombre_completo SEPARATOR ', ') as pilotos
        FROM fact_resultado_carrera f
        JOIN dim_constructor c ON f.constructor_id = c.constructor_id
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE {where_sql}
        GROUP BY t.anio
        ORDER BY t.anio
    """
    return ejecutar_query(query)

def get_comparacion_circuitos(circuito1, circuito2):
    """Comparar estadísticas entre dos circuitos"""
    query = f"""
        SELECT 
            circ.nombre as circuito,
            COUNT(DISTINCT f.carrera_id) as carreras_disputadas,
            COUNT(DISTINCT f.piloto_id) as pilotos_diferentes,
            COUNT(DISTINCT f.constructor_id) as constructores_diferentes,
            AVG(f.velocidad_promedio) as velocidad_promedio,
            MIN(t.anio) as primera_carrera,
            MAX(t.anio) as ultima_carrera
        FROM fact_resultado_carrera f
        JOIN dim_circuito circ ON f.circuito_id = circ.circuito_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE circ.nombre IN ('{circuito1}', '{circuito2}')
        GROUP BY circ.circuito_id, circ.nombre
    """
    return ejecutar_query(query)

def get_evolucion_puntos_constructor(constructor):
    """Evolución de puntos totales por año para un constructor"""
    query = f"""
        SELECT 
            t.anio,
            SUM(f.puntos) as puntos_totales,
            COUNT(DISTINCT f.piloto_id) as pilotos_diferentes,
            COUNT(DISTINCT f.carrera_id) as carreras_disputadas,
            SUM(f.es_victoria) as victorias,
            SUM(f.es_podio) as podios
        FROM fact_resultado_carrera f
        JOIN dim_constructor c ON f.constructor_id = c.constructor_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE c.nombre = '{constructor}'
        GROUP BY t.anio
        ORDER BY t.anio
    """
    return ejecutar_query(query)

def get_lista_anios():
    """Obtener lista de años disponibles"""
    query = """
        SELECT DISTINCT anio
        FROM dim_tiempo
        ORDER BY anio DESC
    """
    return ejecutar_query(query)

def get_lista_pilotos():
    """Obtener lista de pilotos"""
    query = """
        SELECT DISTINCT nombre_completo
        FROM dim_piloto
        ORDER BY nombre_completo
    """
    return ejecutar_query(query)

def get_lista_pilotos_por_anio(anio):
    """Obtener lista de pilotos que corrieron en un año específico"""
    query = f"""
        SELECT DISTINCT p.nombre_completo
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE t.anio = {anio}
        ORDER BY p.nombre_completo
    """
    return ejecutar_query(query)

def get_evolucion_campeonato_por_carreras(anio):
    """Evolución del campeonato carrera por carrera en un año específico
    Retorna puntos acumulados de cada piloto después de cada carrera
    """
    query = f"""
        WITH carreras_ordenadas AS (
            SELECT DISTINCT 
                ca.carrera_id,
                ca.ronda,
                ca.nombre_gp,
                t.fecha
            FROM dim_carrera ca
            JOIN dim_tiempo t ON ca.fecha = t.fecha
            WHERE t.anio = {anio}
            ORDER BY ca.ronda
        ),
        puntos_por_carrera AS (
            SELECT 
                ca.ronda,
                ca.nombre_gp,
                p.nombre_completo as piloto,
                c.nombre as constructor,
                f.puntos,
                SUM(f.puntos) OVER (
                    PARTITION BY p.piloto_id 
                    ORDER BY ca.ronda
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) as puntos_acumulados
            FROM fact_resultado_carrera f
            JOIN dim_piloto p ON f.piloto_id = p.piloto_id
            JOIN dim_constructor c ON f.constructor_id = c.constructor_id
            JOIN dim_carrera ca ON f.carrera_id = ca.carrera_id
            JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
            WHERE t.anio = {anio}
        )
        SELECT 
            ronda,
            nombre_gp,
            piloto,
            constructor,
            puntos,
            puntos_acumulados
        FROM puntos_por_carrera
        ORDER BY ronda, puntos_acumulados DESC
    """
    return ejecutar_query(query)

def get_colores_constructores():
    """Mapeo de colores por constructor para consistencia visual"""
    # Colores oficiales aproximados de equipos F1
    colores = {
        'Mercedes': '#00D2BE',
        'Ferrari': '#DC0000',
        'Red Bull': '#0600EF',
        'Red Bull Racing': '#0600EF',
        'McLaren': '#FF8700',
        'Alpine': '#0090FF',
        'Aston Martin': '#006F62',
        'AlphaTauri': '#2B4562',
        'Alfa Romeo': '#900000',
        'Haas': '#FFFFFF',
        'Williams': '#005AFF',
        'Racing Point': '#F596C8',
        'Renault': '#FFF500',
        'Toro Rosso': '#469BFF',
        'Force India': '#F596C8',
        'Sauber': '#9B0000',
        'Manor': '#6D1F1F',
        'Lotus F1': '#FFB800',
        'Caterham': '#005030',
        'Marussia': '#6D1F1F',
        'HRT': '#5A5A5A',
        'Virgin': '#C00000',
        'Brawn': '#FFD800',
        'BMW Sauber': '#1E5BC6',
        'Toyota': '#E40000',
        'Honda': '#F0F0F0',
        'Super Aguri': '#FF6600',
        'Spyker': '#FF8000',
        'Midland': '#FF1E00',
        'Jordan': '#FFED00',
        'Minardi': '#000000',
        'Jaguar': '#004225',
        'BAR': '#006699',
        'Prost': '#0057A8',
        'Arrows': '#FF6633',
        'Benetton': '#1E3D8F',
        'Stewart': '#FFFFFF',
        'Tyrrell': '#0057A8',
        'Ligier': '#0066CC',
        'Footwork': '#FF1E00',
        'Larrousse': '#FF6600',
        'Simtek': '#7B68EE',
        'Pacific': '#00A3E0',
        'Forti': '#C0C0C0'
    }
    return colores

def get_comparacion_pilotos_por_anio(anio, piloto):
    """Comparar puntos de un piloto vs todos los demás en un año específico"""
    query = f"""
        SELECT 
            p.nombre_completo as piloto,
            c.nombre as constructor,
            SUM(f.puntos) as puntos_totales,
            COUNT(*) as carreras_disputadas,
            SUM(f.es_victoria) as victorias,
            SUM(f.es_podio) as podios,
            SUM(f.es_pole) as poles,
            CASE WHEN p.nombre_completo = '{piloto}' THEN 1 ELSE 0 END as es_piloto_seleccionado
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        JOIN dim_constructor c ON f.constructor_id = c.constructor_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE t.anio = {anio}
        GROUP BY p.piloto_id, p.nombre_completo, c.constructor_id, c.nombre
        ORDER BY puntos_totales DESC
    """
    return ejecutar_query(query)

def get_evolucion_piloto_por_carreras_anio(anio, piloto):
    """Evolución carrera por carrera de un piloto en un año"""
    query = f"""
        SELECT 
            ca.nombre_gp,
            ca.ronda,
            f.puntos,
            f.posicion_final,
            f.posicion_salida,
            circ.nombre as circuito,
            t.fecha
        FROM fact_resultado_carrera f
        JOIN dim_piloto p ON f.piloto_id = p.piloto_id
        JOIN dim_carrera ca ON f.carrera_id = ca.carrera_id
        JOIN dim_circuito circ ON f.circuito_id = circ.circuito_id
        JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
        WHERE t.anio = {anio}
          AND p.nombre_completo = '{piloto}'
        ORDER BY ca.ronda
    """
    return ejecutar_query(query)

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    # HEADER
    st.title("🏎️ F1 Data Warehouse Dashboard")
    st.markdown("### Análisis de Fórmula 1 (1950-2024) - Metodología Hefesto")
    st.markdown("---")
    
    # SIDEBAR
    st.sidebar.title("📊 Navegación")
    st.sidebar.markdown("---")
    
    pagina = st.sidebar.radio(
        "Selecciona una sección:",
        [
            "🏠 Overview",
            "🏆 Campeonatos y Victorias",
            "🥇 Pole Positions",
            "� Análisis de Circuitos",
            "⏱️ Tiempos de Vuelta",
            "� Análisis de Constructores",
            "� Comparación de Pilotos"
        ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Tip:** Los datos se actualizan cada 10 minutos")
    
    # ========================================================================
    # PÁGINA: OVERVIEW
    # ========================================================================
    
    if pagina == "🏠 Overview":
        st.header("📊 Resumen General del Data Warehouse")
        
        # Estadísticas generales
        stats = get_estadisticas_generales()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👤 Pilotos", f"{stats['total_pilotos'].iloc[0]:,}")
            st.metric("🏎️ Constructores", f"{stats['total_constructores'].iloc[0]:,}")
        
        with col2:
            st.metric("🏁 Circuitos", f"{stats['total_circuitos'].iloc[0]:,}")
            st.metric("🏆 Carreras", f"{stats['total_carreras'].iloc[0]:,}")
        
        with col3:
            st.metric("📝 Resultados", f"{stats['total_resultados'].iloc[0]:,}")
            st.metric("🥇 Victorias", f"{stats['total_victorias'].iloc[0]:,}")
        
        with col4:
            st.metric("🏅 Podios", f"{stats['total_podios'].iloc[0]:,}")
            st.metric("⚡ Poles", f"{stats['total_poles'].iloc[0]:,}")
        
        st.markdown("---")
        
        # Evolución de carreras por año
        st.subheader("📈 Evolución del Calendario F1")
        df_carreras = get_carreras_por_año()
        
        fig = px.area(
            df_carreras,
            x='anio',
            y='total_carreras',
            title='Total de Carreras por Temporada (1950-2024)',
            labels={'anio': 'Año', 'total_carreras': 'Número de Carreras'}
        )
        fig.update_traces(
            fill='tozeroy',
            fillcolor='rgba(225, 6, 0, 0.2)',
            line_color='#E10600',
            line_width=3
        )
        fig.update_layout(
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Explorador de Campeones por Año
        st.subheader("🏆 Explorador de Campeones Mundiales")
        st.markdown("**Selecciona un año para ver los campeones de esa temporada**")
        
        # Selector de año
        años_disponibles = sorted(df_carreras['anio'].unique(), reverse=True)
        año_seleccionado = st.selectbox(
            "Año:",
            options=años_disponibles,
            index=0  # Por defecto el año más reciente
        )
        
        # Obtener información del año seleccionado
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"#### 🏁 Temporada {año_seleccionado}")
            
            # Estadísticas del año
            stats_año = get_estadisticas_año(año_seleccionado)
            if not stats_año.empty:
                st.metric("🏆 Carreras Disputadas", f"{stats_año['carreras'].iloc[0]}")
                st.metric("👤 Pilotos Participantes", f"{stats_año['pilotos_participantes'].iloc[0]}")
                st.metric("🚗 Constructores", f"{stats_año['constructores'].iloc[0]}")
                st.metric("🏁 Circuitos Diferentes", f"{stats_año['circuitos_diferentes'].iloc[0]}")
        
        with col2:
            st.markdown(f"#### 🏆 Campeones {año_seleccionado}")
            
            # Campeón de Pilotos
            campeon_piloto = get_campeon_piloto_por_año(año_seleccionado)
            if not campeon_piloto.empty:
                st.success(f"**🥇 Campeón de Pilotos**")
                st.markdown(f"### {campeon_piloto['campeon_piloto'].iloc[0]}")
                st.metric("Puntos Totales", f"{campeon_piloto['puntos_totales'].iloc[0]:.1f}")
                st.metric("Victorias", f"{int(campeon_piloto['victorias'].iloc[0])}")
            
            # Campeón de Constructores (desde 1958)
            if año_seleccionado >= 1958:
                campeon_constructor = get_campeon_constructor_por_año(año_seleccionado)
                if not campeon_constructor.empty:
                    st.info(f"**🏎️ Campeón de Constructores**")
                    st.markdown(f"### {campeon_constructor['campeon_constructor'].iloc[0]}")
                    st.metric("Puntos Totales", f"{campeon_constructor['puntos_totales'].iloc[0]:.1f}")
                    st.metric("Victorias", f"{int(campeon_constructor['victorias'].iloc[0])}")
            else:
                st.warning("El campeonato de constructores comenzó en 1958")
    
    # ========================================================================
    # PÁGINA: CAMPEONATOS Y VICTORIAS
    # ========================================================================
    
    elif pagina == "🏆 Campeonatos y Victorias":
        st.header("🏆 Campeonatos y Victorias")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🥇 Top 10 Pilotos con Más Victorias")
            df_victorias = get_top_pilotos_victorias(10)
            
            fig = px.bar(
                df_victorias,
                x='victorias',
                y='nombre_completo',
                orientation='h',
                color='victorias',
                color_continuous_scale='Reds',
                labels={'victorias': 'Victorias', 'nombre_completo': 'Piloto'}
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_victorias, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("📊 Top Piloto por Década")
            df_decada = get_mejor_piloto_por_decada()
            
            fig = px.bar(
                df_decada,
                x='decada',
                y='victorias',
                color='nombre_completo',
                labels={'decada': 'Década', 'victorias': 'Victorias', 'nombre_completo': 'Piloto'}
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_decada[['decada', 'nombre_completo', 'victorias']], 
                        use_container_width=True, hide_index=True)
    
    # ========================================================================
    # PÁGINA: POLE POSITIONS
    # ========================================================================
    
    elif pagina == "🥇 Pole Positions":
        st.header("⚡ Análisis de Pole Positions")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🥇 Top 10 Pilotos con Más Poles")
            df_poles = get_top_pilotos_poles(10)
            
            fig = px.bar(
                df_poles,
                x='nombre_completo',
                y='poles',
                color='poles',
                color_continuous_scale='Blues',
                labels={'poles': 'Pole Positions', 'nombre_completo': 'Piloto'}
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📊 Conversión Pole → Victoria")
            df_conv = get_conversion_pole_victoria()
            
            st.metric(
                "Tasa de Conversión",
                f"{df_conv['porcentaje_conversion'].iloc[0]}%",
                help="Porcentaje de victorias que vinieron desde pole position"
            )
            
            st.metric(
                "Poles con Victoria",
                f"{df_conv['poles_con_victoria'].iloc[0]:,}"
            )
            
            st.metric(
                "Total Victorias",
                f"{df_conv['total_victorias'].iloc[0]:,}"
            )
        
        st.markdown("---")
        st.dataframe(df_poles, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # PÁGINA: ANÁLISIS DE CIRCUITOS
    # ========================================================================
    
    elif pagina == "� Análisis de Circuitos":
        st.header("🌍 Análisis de Circuitos")
        st.markdown("Explora la distribución geográfica y comparación de circuitos")
        st.markdown("---")
        
        # ====================================================================
        # SUB-SECCIÓN 1: DISTRIBUCIÓN POR CONTINENTE
        # ====================================================================
        
        st.subheader("🌍 Distribución de Circuitos por Continente")
        st.markdown("**Selecciona el período de análisis**")
        
        # Selector de tipo de vista
        tipo_vista = st.radio(
            "Tipo de análisis:",
            options=["📊 Vista Global (Histórico Completo)", "📅 Por Año(s) Específico(s)"],
            horizontal=True
        )
        
        anios_filtro = None
        
        if tipo_vista == "📅 Por Año(s) Específico(s)":
            # Obtener años disponibles
            df_anios_disponibles = get_lista_anios()
            anios_disponibles = sorted(df_anios_disponibles['anio'].tolist(), reverse=True)
            
            # Selector múltiple de años
            anios_seleccionados = st.multiselect(
                "Selecciona uno o más años:",
                options=anios_disponibles,
                default=[anios_disponibles[0]]  # Por defecto el año más reciente
            )
            
            if len(anios_seleccionados) > 0:
                anios_filtro = anios_seleccionados
                st.info(f"📅 Mostrando circuitos que disputaron carreras en: {', '.join(map(str, sorted(anios_seleccionados)))}")
            else:
                st.warning("⚠️ Selecciona al menos un año para filtrar")
        else:
            st.info("📊 Mostrando todos los circuitos registrados en la base de datos (1950-2024)")
        
        # Obtener datos según filtro
        df_continentes = get_circuitos_por_continente(anios_filtro)
        
        if not df_continentes.empty:
            # Definir paleta de colores consistente para ambos gráficos
            color_map = {
                'Europa': '#636EFA',      # Azul
                'Asia': '#EF553B',        # Rojo
                'América': '#00CC96',     # Verde/Turquesa
                'Oceanía': '#AB63FA',     # Morado
                'África': '#FFA15A',      # Naranja
                'Otros': '#19D3F3'        # Cyan
            }
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Determinar título según el tipo de vista
                if anios_filtro:
                    titulo_grafico = f'Circuitos por Continente ({", ".join(map(str, sorted(anios_filtro)))})'
                else:
                    titulo_grafico = 'Circuitos por Continente (Histórico)'
                
                fig = px.bar(
                    df_continentes,
                    x='continente',
                    y='cantidad_circuitos',
                    color='continente',
                    color_discrete_map=color_map,
                    labels={'continente': 'Continente', 'cantidad_circuitos': 'Cantidad de Circuitos'},
                    title=titulo_grafico
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig_pie = px.pie(
                    df_continentes,
                    values='cantidad_circuitos',
                    names='continente',
                    title='Distribución Porcentual',
                    hole=0.4,  # Donut chart para mejor visualización
                    color='continente',
                    color_discrete_map=color_map
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            
            # Métricas adicionales si hay filtro por año
            if anios_filtro and 'carreras_disputadas' in df_continentes.columns:
                st.markdown("#### 📊 Estadísticas del Período Seleccionado")
                col_m1, col_m2, col_m3 = st.columns(3)
                
                with col_m1:
                    st.metric("🏁 Total de Circuitos", int(df_continentes['cantidad_circuitos'].sum()))
                with col_m2:
                    st.metric("🏆 Carreras Disputadas", int(df_continentes['carreras_disputadas'].sum()))
                with col_m3:
                    promedio = df_continentes['carreras_disputadas'].sum() / df_continentes['cantidad_circuitos'].sum()
                    st.metric("📈 Promedio Carreras/Circuito", f"{promedio:.1f}")
            
            # Tabla expandible con detalles
            with st.expander("🔍 Ver lista detallada de circuitos por continente"):
                st.dataframe(df_continentes, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No hay datos disponibles para los años seleccionados")
        
        st.markdown("---")
        
        # ====================================================================
        # SUB-SECCIÓN 2: COMPARACIÓN ENTRE CIRCUITOS
        # ====================================================================
        
        st.subheader("🏁 Comparación entre Circuitos")
        st.markdown("**Compara estadísticas entre dos circuitos diferentes**")
        
        df_circuitos = get_lista_circuitos()
        
        col1, col2 = st.columns(2)
        
        with col1:
            circuito1 = st.selectbox(
                "🏁 Circuito 1:",
                df_circuitos['nombre'].tolist(),
                index=0,
                key='circuito1'
            )
        
        with col2:
            circuito2 = st.selectbox(
                "🏁 Circuito 2:",
                df_circuitos['nombre'].tolist(),
                index=1 if len(df_circuitos) > 1 else 0,
                key='circuito2'
            )
        
        if st.button("⚖️ Comparar Circuitos", type="primary", key='btn_comparar_circuitos'):
            if circuito1 == circuito2:
                st.error("⚠️ Por favor selecciona dos circuitos diferentes")
            else:
                with st.spinner("Comparando circuitos..."):
                    df_comparacion = get_comparacion_circuitos(circuito1, circuito2)
                    
                    if len(df_comparacion) > 0:
                        # Mostrar comparación lado a lado
                        col1, col2 = st.columns(2)
                        
                        for idx, row in df_comparacion.iterrows():
                            col = col1 if idx == 0 else col2
                            
                            with col:
                                st.markdown(f"### {row['circuito']}")
                                st.metric("Carreras Disputadas", f"{row['carreras_disputadas']:.0f}")
                                st.metric("Pilotos Diferentes", f"{row['pilotos_diferentes']:.0f}")
                                st.metric("Constructores", f"{row['constructores_diferentes']:.0f}")
                                st.metric("Velocidad Promedio", f"{row['velocidad_promedio']:.2f} km/h" if pd.notna(row['velocidad_promedio']) else "N/A")
                                st.metric("Primera Carrera", f"{row['primera_carrera']:.0f}")
                                st.metric("Última Carrera", f"{row['ultima_carrera']:.0f}")
                        
                        # Gráfico de comparación
                        st.markdown("---")
                        fig = px.bar(
                            df_comparacion,
                            x='circuito',
                            y=['carreras_disputadas', 'pilotos_diferentes', 'constructores_diferentes'],
                            barmode='group',
                            title='Comparación de Estadísticas',
                            labels={'value': 'Cantidad', 'variable': 'Métrica'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # ====================================================================
        # SUB-SECCIÓN 3: PILOTOS CON MÁS VICTORIAS POR CIRCUITO
        # ====================================================================
        
        st.subheader("🏆 Piloto con Más Victorias por Circuito (Top 20)")
        df_circuitos_victorias = get_mejor_piloto_por_circuito()
        
        fig = px.bar(
            df_circuitos_victorias,
            x='victorias',
            y='circuito',
            orientation='h',
            color='piloto',
            labels={'victorias': 'Victorias', 'circuito': 'Circuito', 'piloto': 'Piloto'}
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=800)
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("🔍 Ver tabla detallada"):
            st.dataframe(df_circuitos_victorias, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # PÁGINA: TIEMPOS DE VUELTA
    # ========================================================================
    
    elif pagina == "⏱️ Tiempos de Vuelta":
        st.header("⏱️ Análisis de Tiempos de Vuelta")
        st.markdown("Compara la evolución de tiempos de vuelta por constructor y circuito")
        st.markdown("---")
        
        # ====================================================================
        # EVOLUCIÓN DE TIEMPOS POR CONSTRUCTOR Y CIRCUITO
        # ====================================================================
        
        st.subheader("⏱️ Evolución de Mejor Vuelta: Constructor vs Promedio General")
        st.markdown("**Compara cómo evolucionó la mejor vuelta de un constructor específico versus el promedio de todos los equipos en un circuito**")
        
        # Información sobre disponibilidad de datos
        st.info("ℹ️ **Nota:** Los datos de tiempo de mejor vuelta están disponibles desde **2004 en adelante**. "
                "Mostrando solo constructores activos en los últimos 4 años consecutivos (2021-2024).")
        
        col1, col2 = st.columns(2)
        
        # Obtener listas para los selectores
        df_constructores = get_lista_constructores_activos_recientes()
        df_circuitos = get_lista_circuitos()
        
        if df_constructores.empty:
            st.warning("⚠️ No hay constructores que hayan participado en los últimos 4 años consecutivos.")
        else:
            with col1:
                constructor_seleccionado = st.selectbox(
                    "🏎️ Selecciona un Constructor Activo:",
                    df_constructores['nombre'].tolist(),
                    index=0
                )
            
            with col2:
                circuito_seleccionado = st.selectbox(
                    "🏁 Selecciona un Circuito:",
                    df_circuitos['nombre'].tolist(),
                    index=0
                )
            
            # Botón para ejecutar análisis
            if st.button("🔍 Analizar Evolución de Tiempos", type="primary"):
                with st.spinner(f"Analizando {constructor_seleccionado} en {circuito_seleccionado}..."):
                    df_evolucion = get_evolucion_tiempos_constructor_circuito(
                    constructor_seleccionado,
                    circuito_seleccionado
                )
                
                if len(df_evolucion) > 0:
                    st.success(f"✅ Encontrados {len(df_evolucion)} años de datos")
                    
                    # Gráfico de evolución con dos líneas
                    fig = go.Figure()
                    
                    # Línea del constructor seleccionado
                    fig.add_trace(go.Scatter(
                        x=df_evolucion['anio'],
                        y=df_evolucion['mejor_vuelta_constructor'],
                        mode='lines+markers',
                        name=f'{constructor_seleccionado}',
                        line=dict(color='#E10600', width=3),
                        marker=dict(size=10, symbol='circle'),
                        hovertemplate='<b>%{fullData.name}</b><br>Año: %{x}<br>Mejor Vuelta: %{y:.3f} min<extra></extra>'
                    ))
                    
                    # Línea del promedio general
                    fig.add_trace(go.Scatter(
                        x=df_evolucion['anio'],
                        y=df_evolucion['mejor_vuelta_promedio'],
                        mode='lines+markers',
                        name='Promedio General (Todos los Constructores)',
                        line=dict(color='#00D2BE', width=2, dash='dash'),
                        marker=dict(size=7, symbol='diamond'),
                        hovertemplate='<b>%{fullData.name}</b><br>Año: %{x}<br>Mejor Vuelta: %{y:.3f} min<extra></extra>'
                    ))
                    
                    # Área sombreada cuando el constructor está por debajo del promedio (mejor rendimiento)
                    fig.add_trace(go.Scatter(
                        x=df_evolucion['anio'],
                        y=df_evolucion['mejor_vuelta_promedio'],
                        fill=None,
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=df_evolucion['anio'],
                        y=df_evolucion['mejor_vuelta_constructor'],
                        fill='tonexty',
                        mode='lines',
                        line=dict(width=0),
                        fillcolor='rgba(0, 210, 190, 0.2)',
                        name='Mejor que promedio',
                        hoverinfo='skip'
                    ))
                    
                    fig.update_layout(
                        title=f"Evolución de Mejor Vuelta: {constructor_seleccionado} vs Promedio General<br><sub>{circuito_seleccionado}</sub>",
                        xaxis_title="Año",
                        yaxis_title="Mejor Vuelta (minutos)",
                        hovermode='x unified',
                        height=550,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Métricas resumen
                    st.markdown("#### 📊 Estadísticas Clave")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        mejor_vuelta_constructor = df_evolucion['mejor_vuelta_constructor'].min()
                        año_mejor = df_evolucion.loc[df_evolucion['mejor_vuelta_constructor'].idxmin(), 'anio']
                        st.metric(
                            f"🏆 Mejor Vuelta {constructor_seleccionado}",
                            f"{mejor_vuelta_constructor:.3f} min",
                            delta=f"Año {año_mejor:.0f}"
                        )
                    
                    with col2:
                        promedio_constructor = df_evolucion['mejor_vuelta_constructor'].mean()
                        st.metric(
                            f"📊 Promedio {constructor_seleccionado}",
                            f"{promedio_constructor:.3f} min"
                        )
                    
                    with col3:
                        promedio_general = df_evolucion['mejor_vuelta_promedio'].mean()
                        st.metric(
                            "🌐 Promedio General Histórico",
                            f"{promedio_general:.3f} min"
                        )
                    
                    with col4:
                        años_mejor_que_promedio = (df_evolucion['mejor_vuelta_constructor'] < df_evolucion['mejor_vuelta_promedio']).sum()
                        porcentaje = (años_mejor_que_promedio / len(df_evolucion)) * 100
                        st.metric(
                            "✨ Años Mejor que Promedio",
                            f"{años_mejor_que_promedio}/{len(df_evolucion)}",
                            delta=f"{porcentaje:.1f}%"
                        )
                    
                    # Análisis de rendimiento relativo
                    st.markdown("#### 📈 Análisis de Rendimiento Relativo")
                    
                    # Gráfico de diferencias
                    fig_diff = go.Figure()
                    
                    colores = ['green' if x < 0 else 'red' for x in df_evolucion['diferencia_vs_promedio']]
                    
                    fig_diff.add_trace(go.Bar(
                        x=df_evolucion['anio'],
                        y=df_evolucion['diferencia_vs_promedio'],
                        marker_color=colores,
                        name='Diferencia',
                        hovertemplate='<b>Año %{x}</b><br>Diferencia: %{y:.3f} min<br><extra></extra>'
                    ))
                    
                    fig_diff.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Promedio")
                    
                    fig_diff.update_layout(
                        title=f"Diferencia vs Promedio General (valores negativos = mejor rendimiento)",
                        xaxis_title="Año",
                        yaxis_title="Diferencia (minutos)",
                        height=400,
                        plot_bgcolor='rgba(0,0,0,0)',
                        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
                    )
                    
                    st.plotly_chart(fig_diff, use_container_width=True)
                    
                    # Tabla de datos
                    with st.expander("📋 Ver datos detallados año por año"):
                        df_display = df_evolucion.copy()
                        df_display['mejor_vuelta_constructor'] = df_display['mejor_vuelta_constructor'].round(3)
                        df_display['mejor_vuelta_promedio'] = df_display['mejor_vuelta_promedio'].round(3)
                        df_display['diferencia_vs_promedio'] = df_display['diferencia_vs_promedio'].round(3)
                        st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                else:
                    st.warning(f"⚠️ No hay datos de mejor vuelta disponibles para {constructor_seleccionado} en {circuito_seleccionado}")
                    st.info("💡 **Posibles razones:**\n"
                           "- El constructor no compitió en este circuito durante 2004-2024\n"
                           "- Los datos de mejor vuelta solo están disponibles desde 2004\n"
                           "- Prueba con otros constructores activos en circuitos actuales")
            else:
                st.info("👆 Selecciona un constructor y un circuito, luego haz clic en 'Analizar Evolución de Tiempos'")
    
    # ========================================================================
    # PÁGINA: ANÁLISIS DE CONSTRUCTORES
    # ========================================================================
    
    elif pagina == "🚗 Análisis de Constructores":
        st.header("🚗 Análisis de Constructores")
        st.markdown("Explora el rendimiento y evolución de los constructores")
        st.markdown("---")
        
        # ====================================================================
        # SUB-SECCIÓN 1: RELACIÓN PUNTOS/CARRERA
        # ====================================================================
        
        st.subheader("📊 Mejor Relación Puntos/Carrera (min. 100 carreras)")
        df_const = get_constructores_performance()
        
        fig = px.scatter(
            df_const,
            x='carreras_disputadas',
            y='puntos_por_carrera',
            size='puntos_totales',
            color='puntos_por_carrera',
            hover_name='constructor',
            color_continuous_scale='Viridis',
            labels={
                'carreras_disputadas': 'Carreras Disputadas',
                'puntos_por_carrera': 'Puntos por Carrera',
                'puntos_totales': 'Puntos Totales'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("🔍 Ver tabla detallada"):
            st.dataframe(df_const, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # ====================================================================
        # SUB-SECCIÓN 2: VICTORIAS POR CONSTRUCTOR CON FILTROS
        # ====================================================================
        
        st.subheader("🏆 Victorias Filtradas por Constructor y Década")
        st.markdown("**Analiza victorias aplicando filtros personalizados**")
        
        df_constructores = get_lista_constructores()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filtro_constructor = st.selectbox(
                "🏎️ Constructor (opcional):",
                ['Todos'] + df_constructores['nombre'].tolist(),
                key='filtro_constructor'
            )
        
        with col2:
            filtro_decada = st.selectbox(
                "📅 Década (opcional):",
                ['Todas', 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020],
                key='filtro_decada'
            )
        
        with col3:
            st.markdown("")
            st.markdown("")
            aplicar_filtros = st.button("🔍 Aplicar Filtros", type="primary", key='btn_filtros')
        
        if aplicar_filtros:
            constructor_param = None if filtro_constructor == 'Todos' else filtro_constructor
            decada_param = None if filtro_decada == 'Todas' else filtro_decada
            
            with st.spinner("Aplicando filtros..."):
                df_victorias_filtradas = get_victorias_por_constructor_filtrado(
                    constructor_param,
                    decada_param
                )
                
                if len(df_victorias_filtradas) > 0:
                    st.success(f"✅ Encontradas {df_victorias_filtradas['victorias'].sum():.0f} victorias")
                    
                    fig = px.line(
                        df_victorias_filtradas,
                        x='anio',
                        y='victorias',
                        title=f"Victorias por Año - {filtro_constructor} - {filtro_decada}",
                        labels={'anio': 'Año', 'victorias': 'Victorias'},
                        markers=True
                    )
                    fig.update_traces(line_color='#E10600')
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("Ver detalle por año"):
                        st.dataframe(df_victorias_filtradas, use_container_width=True, hide_index=True)
                else:
                    st.warning("⚠️ No se encontraron victorias con los filtros seleccionados")
        
        st.markdown("---")
        
        # ====================================================================
        # SUB-SECCIÓN 3: EVOLUCIÓN DE PUNTOS POR CONSTRUCTOR
        # ====================================================================
        
        st.subheader("📈 Evolución de Puntos por Constructor (Temporada a Temporada)")
        st.markdown("**Analiza cómo evolucionaron los puntos de un constructor a lo largo de su historia**")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            constructor_puntos = st.selectbox(
                "🏎️ Selecciona un Constructor:",
                df_constructores['nombre'].tolist(),
                index=0,
                key='constructor_puntos'
            )
        
        with col2:
            st.markdown("")
            st.markdown("")
            analizar_puntos = st.button("📈 Analizar Evolución de Puntos", type="primary", key='btn_puntos')
        
        if analizar_puntos:
            with st.spinner(f"Analizando evolución de {constructor_puntos}..."):
                df_puntos_constructor = get_evolucion_puntos_constructor(constructor_puntos)
                
                if len(df_puntos_constructor) > 0:
                    st.success(f"✅ Datos de {len(df_puntos_constructor)} temporadas")
                    
                    # Gráfico principal: Evolución de puntos
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatter(
                        x=df_puntos_constructor['anio'],
                        y=df_puntos_constructor['puntos_totales'],
                        mode='lines+markers',
                        name='Puntos Totales',
                        line=dict(color='#E10600', width=3),
                        marker=dict(size=8),
                        fill='tozeroy',
                        fillcolor='rgba(225, 6, 0, 0.1)'
                    ))
                    
                    fig.update_layout(
                        title=f"Evolución de Puntos: {constructor_puntos} (Por Temporada)",
                        xaxis_title="Año",
                        yaxis_title="Puntos Totales",
                        hovermode='x unified',
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Métricas resumen
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        mejor_temporada = df_puntos_constructor.loc[df_puntos_constructor['puntos_totales'].idxmax()]
                        st.metric(
                            "Mejor Temporada",
                            f"{mejor_temporada['anio']:.0f}",
                            delta=f"{mejor_temporada['puntos_totales']:.0f} puntos"
                        )
                    
                    with col2:
                        st.metric(
                            "Puntos Totales Históricos",
                            f"{df_puntos_constructor['puntos_totales'].sum():,.0f}"
                        )
                    
                    with col3:
                        st.metric(
                            "Victorias Totales",
                            f"{df_puntos_constructor['victorias'].sum():.0f}"
                        )
                    
                    with col4:
                        st.metric(
                            "Temporadas Activas",
                            f"{len(df_puntos_constructor)}"
                        )
                    
                    # Gráfico secundario: Victorias y Podios por año
                    st.markdown("#### 🏆 Victorias y Podios por Temporada")
                    
                    fig2 = go.Figure()
                    
                    fig2.add_trace(go.Bar(
                        x=df_puntos_constructor['anio'],
                        y=df_puntos_constructor['victorias'],
                        name='Victorias',
                        marker_color='gold'
                    ))
                    
                    fig2.add_trace(go.Bar(
                        x=df_puntos_constructor['anio'],
                        y=df_puntos_constructor['podios'],
                        name='Podios',
                        marker_color='silver'
                    ))
                    
                    fig2.update_layout(
                        barmode='group',
                        xaxis_title="Año",
                        yaxis_title="Cantidad",
                        hovermode='x unified',
                        height=400
                    )
                    
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Tabla de datos detallada
                    with st.expander("Ver datos detallados por temporada"):
                        st.dataframe(
                            df_puntos_constructor.style.background_gradient(
                                subset=['puntos_totales'], 
                                cmap='Reds'
                            ),
                            use_container_width=True,
                            hide_index=True
                        )
                else:
                    st.warning(f"⚠️ No hay datos disponibles para {constructor_puntos}")
    
    # ========================================================================
    # PÁGINA: COMPARACIÓN DE PILOTOS
    # ========================================================================
    
    elif pagina == "🏁 Comparación de Pilotos":
        st.header("🏁 Comparación de Pilotos")
        st.markdown("Analiza el rendimiento de pilotos y la evolución del campeonato carrera por carrera")
        st.markdown("---")
        
        # ====================================================================
        # COMPARACIÓN DE PILOTOS POR TEMPORADA
        # ====================================================================
        
        st.subheader("🏁 Análisis de Pilotos por Temporada")
        st.markdown("**Analiza el rendimiento de pilotos y la evolución del campeonato carrera por carrera**")
        
        # Selector de año
        df_anios = get_lista_anios()
        
        anio_seleccionado = st.selectbox(
            "📅 Selecciona una Temporada:",
            df_anios['anio'].tolist(),
            index=0,
            key='anio_comparacion_temporada'
        )
        
        # Obtener pilotos que corrieron ese año
        df_pilotos_anio = get_lista_pilotos_por_anio(anio_seleccionado)
        
        if df_pilotos_anio.empty:
            st.warning(f"⚠️ No hay datos de pilotos para el año {anio_seleccionado}")
        else:
            # Tabs para diferentes análisis
            tab1, tab2 = st.tabs(["🏆 Evolución del Campeonato", "⚖️ Comparación Individual"])
            
            # ================================================================
            # TAB 1: EVOLUCIÓN DEL CAMPEONATO CARRERA POR CARRERA
            # ================================================================
            with tab1:
                st.markdown(f"### 📊 Evolución del Campeonato {anio_seleccionado} - Carrera por Carrera")
                st.markdown("Puntos acumulados de cada piloto a lo largo de la temporada, con colores por escudería")
                
                with st.spinner("Calculando evolución del campeonato..."):
                    df_evolucion_campeonato = get_evolucion_campeonato_por_carreras(anio_seleccionado)
                    
                    if not df_evolucion_campeonato.empty:
                        # Obtener top pilotos para el gráfico (evitar saturación)
                        num_pilotos_mostrar = st.slider(
                            "Número de pilotos a mostrar:",
                            min_value=5,
                            max_value=20,
                            value=10,
                            step=1,
                            key='slider_pilotos_evolucion'
                        )
                        
                        # Identificar top pilotos por puntos finales
                        puntos_finales = df_evolucion_campeonato.groupby('piloto')['puntos_acumulados'].max()
                        top_pilotos = puntos_finales.nlargest(num_pilotos_mostrar).index.tolist()
                        
                        # Filtrar datos
                        df_top = df_evolucion_campeonato[df_evolucion_campeonato['piloto'].isin(top_pilotos)]
                        
                        # Crear gráfico de evolución
                        fig = go.Figure()
                        
                        # Obtener colores por constructor
                        colores_constructores = get_colores_constructores()
                        
                        # Agregar línea por cada piloto
                        for piloto in top_pilotos:
                            df_piloto = df_top[df_top['piloto'] == piloto]
                            constructor = df_piloto['constructor'].iloc[0]
                            color = colores_constructores.get(constructor, '#808080')
                            
                            fig.add_trace(go.Scatter(
                                x=df_piloto['ronda'],
                                y=df_piloto['puntos_acumulados'],
                                mode='lines+markers',
                                name=f"{piloto} ({constructor})",
                                line=dict(color=color, width=2.5),
                                marker=dict(size=6, color=color),
                                hovertemplate=f'<b>{piloto}</b><br>' +
                                            'Carrera: %{x}<br>' +
                                            'Puntos Acumulados: %{y}<br>' +
                                            '<extra></extra>'
                            ))
                        
                        fig.update_layout(
                            title=f"Evolución del Campeonato de Pilotos {anio_seleccionado}",
                            xaxis_title="Ronda (Carrera)",
                            yaxis_title="Puntos Acumulados",
                            hovermode='x unified',
                            height=600,
                            legend=dict(
                                orientation="v",
                                yanchor="top",
                                y=0.99,
                                xanchor="left",
                                x=1.01
                            ),
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                            yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabla de clasificación final
                        st.markdown("#### 🏆 Clasificación Final del Campeonato")
                        clasificacion_final = df_evolucion_campeonato.groupby(['piloto', 'constructor']).agg({
                            'puntos_acumulados': 'max',
                            'puntos': 'sum'
                        }).reset_index()
                        clasificacion_final = clasificacion_final.sort_values('puntos_acumulados', ascending=False)
                        clasificacion_final.insert(0, 'Posición', range(1, len(clasificacion_final) + 1))
                        clasificacion_final.columns = ['Posición', 'Piloto', 'Constructor', 'Puntos Totales', 'Verificación']
                        
                        st.dataframe(
                            clasificacion_final[['Posición', 'Piloto', 'Constructor', 'Puntos Totales']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.warning(f"⚠️ No hay datos de evolución para el año {anio_seleccionado}")
            
            # ================================================================
            # TAB 2: COMPARACIÓN INDIVIDUAL DE PILOTO
            # ================================================================
            with tab2:
                st.markdown(f"### ⚖️ Comparación Individual de Piloto en {anio_seleccionado}")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    piloto_seleccionado = st.selectbox(
                        "🏎️ Selecciona un Piloto:",
                        df_pilotos_anio['nombre_completo'].tolist(),
                        index=0,
                        key='piloto_comparacion_individual'
                    )
                
                with col2:
                    st.markdown("")
                    st.markdown("")
                    comparar_pilotos = st.button("⚖️ Comparar", type="primary", key='btn_comparar_pilotos')
                
                if comparar_pilotos:
                    with st.spinner(f"Analizando temporada {anio_seleccionado}..."):
                        df_comparacion_pilotos = get_comparacion_pilotos_por_anio(anio_seleccionado, piloto_seleccionado)
                        df_evolucion_carreras = get_evolucion_piloto_por_carreras_anio(anio_seleccionado, piloto_seleccionado)
                        
                        if len(df_comparacion_pilotos) > 0:
                            # Encontrar posición del piloto seleccionado
                            piloto_row = df_comparacion_pilotos[df_comparacion_pilotos['es_piloto_seleccionado'] == 1]
                            
                            if len(piloto_row) > 0:
                                posicion = piloto_row.index[0] + 1
                                
                                st.success(f"✅ {piloto_seleccionado} terminó en la posición **#{posicion}** del campeonato {anio_seleccionado}")
                                
                                # Métricas del piloto seleccionado
                                col1, col2, col3, col4, col5 = st.columns(5)
                                
                                with col1:
                                    st.metric("Posición Final", f"#{posicion}")
                                
                                with col2:
                                    st.metric("Puntos Totales", f"{piloto_row['puntos_totales'].iloc[0]:.0f}")
                                
                                with col3:
                                    st.metric("Victorias", f"{piloto_row['victorias'].iloc[0]:.0f}")
                                
                                with col4:
                                    st.metric("Podios", f"{piloto_row['podios'].iloc[0]:.0f}")
                                
                                with col5:
                                    st.metric("Poles", f"{piloto_row['poles'].iloc[0]:.0f}")
                                
                                st.markdown("---")
                                
                                # Gráfico de comparación de puntos (Top 15)
                                st.markdown(f"#### 📊 Comparación de Puntos - Temporada {anio_seleccionado} (Top 15)")
                                
                                df_top15 = df_comparacion_pilotos.head(15)
                                
                                # Colorear diferente al piloto seleccionado
                                colors = ['#E10600' if row['es_piloto_seleccionado'] == 1 else '#00D2BE' 
                                         for _, row in df_top15.iterrows()]
                                
                                fig = go.Figure(data=[
                                    go.Bar(
                                        x=df_top15['piloto'],
                                        y=df_top15['puntos_totales'],
                                        marker_color=colors,
                                        text=df_top15['puntos_totales'],
                                        textposition='outside'
                                    )
                                ])
                                
                                fig.update_layout(
                                    xaxis_title="Piloto",
                                    yaxis_title="Puntos Totales",
                                    height=500,
                                    showlegend=False
                                )
                                fig.update_xaxes(tickangle=45)
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Evolución carrera por carrera
                                if len(df_evolucion_carreras) > 0:
                                    st.markdown(f"#### 🏁 Evolución Carrera por Carrera - {piloto_seleccionado}")
                                    
                                    # Calcular puntos acumulados
                                    df_evolucion_carreras['puntos_acumulados'] = df_evolucion_carreras['puntos'].cumsum()
                                    
                                    fig2 = go.Figure()
                                    
                                    # Línea de puntos acumulados
                                    fig2.add_trace(go.Scatter(
                                        x=df_evolucion_carreras['ronda'],
                                        y=df_evolucion_carreras['puntos_acumulados'],
                                        mode='lines+markers',
                                        name='Puntos Acumulados',
                                        line=dict(color='#E10600', width=3),
                                        marker=dict(size=10),
                                        hovertemplate='<b>Carrera %{x}</b><br>' +
                                                    'Puntos Acumulados: %{y}<br>' +
                                                    '<extra></extra>'
                                    ))
                                    
                                    # Barras de puntos por carrera
                                    fig2.add_trace(go.Bar(
                                        x=df_evolucion_carreras['ronda'],
                                        y=df_evolucion_carreras['puntos'],
                                        name='Puntos por Carrera',
                                        marker_color='rgba(0, 210, 190, 0.5)',
                                        yaxis='y2'
                                    ))
                                    
                                    fig2.update_layout(
                                        title=f"Puntos por Carrera y Acumulados - {piloto_seleccionado} ({anio_seleccionado})",
                                        xaxis_title="Ronda",
                                        yaxis_title="Puntos Acumulados",
                                        yaxis2=dict(
                                            title="Puntos por Carrera",
                                            overlaying='y',
                                            side='right'
                                        ),
                                        hovermode='x unified',
                                        height=500
                                    )
                                    
                                    st.plotly_chart(fig2, use_container_width=True)
                                    
                                    # Tabla detallada de carreras
                                    with st.expander("Ver detalle de cada Gran Premio"):
                                        st.dataframe(
                                            df_evolucion_carreras[['ronda', 'nombre_gp', 'circuito', 'posicion_final', 'posicion_salida', 'puntos', 'puntos_acumulados']],
                                            use_container_width=True,
                                            hide_index=True
                                        )
                                
                                # Tabla completa de clasificación
                                with st.expander("Ver clasificación completa del campeonato"):
                                    st.dataframe(
                                        df_comparacion_pilotos[['piloto', 'constructor', 'puntos_totales', 'victorias', 'podios', 'poles', 'carreras_disputadas']],
                                        use_container_width=True,
                                        hide_index=True
                                    )
                            else:
                                st.warning(f"⚠️ {piloto_seleccionado} no participó en la temporada {anio_seleccionado}")
                        else:
                            st.warning(f"⚠️ No hay datos disponibles para la temporada {anio_seleccionado}")

# ============================================================================
# EJECUTAR APP
# ============================================================================

if __name__ == "__main__":
    main()
