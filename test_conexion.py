#!/usr/bin/env python3
"""
Script de verificación de conexión MySQL
Ejecuta este script ANTES del ETL para validar credenciales
"""

import mysql.connector
from mysql.connector import Error

# ============================================================================
# CONFIGURACIÓN - MODIFICA SEGÚN TUS CREDENCIALES
# ============================================================================

DB_CONFIG = {
    'host': 'localhost',      # Cambia si tu MySQL está en otro servidor
    'port': 3306,
    'database': 'mysql',      # Usamos la BD por defecto para testear conexión
    'user': 'root',         
    'password': '' 
}

# ============================================================================
# TESTS DE CONEXIÓN
# ============================================================================

def test_conexion():
    """Verifica conexión básica a MySQL"""
    print("=" * 70)
    print("🔍 TEST 1: Verificando conexión a MySQL")
    print("=" * 70)
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        
        if conn.is_connected():
            db_info = conn.get_server_info()
            cursor = conn.cursor()
            cursor.execute("SELECT DATABASE();")
            record = cursor.fetchone()
            
            print("✅ Conexión exitosa!")
            print(f"   📌 Versión MySQL: {db_info}")
            print(f"   📌 Base de datos actual: {record[0]}")
            
            cursor.close()
            conn.close()
            return True
            
    except Error as e:
        print("❌ Error de conexión:")
        print(f"   {e}")
        return False

def test_crear_database():
    """Verifica permisos para crear base de datos"""
    print("\n" + "=" * 70)
    print("🔍 TEST 2: Verificando permisos para crear base de datos")
    print("=" * 70)
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Intentar crear y eliminar base de datos de prueba
        cursor.execute("CREATE DATABASE IF NOT EXISTS test_permisos")
        cursor.execute("DROP DATABASE test_permisos")
        
        print("✅ Permisos OK - Puedes crear bases de datos")
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print("❌ Error de permisos:")
        print(f"   {e}")
        print("\n💡 Solución: Ejecuta este comando en MySQL:")
        print(f"   GRANT ALL PRIVILEGES ON *.* TO '{DB_CONFIG['user']}'@'localhost';")
        return False

def test_crear_f1_database():
    """Crear base de datos f1_datawarehouse si no existe"""
    print("\n" + "=" * 70)
    print("🔍 TEST 3: Creando base de datos f1_datawarehouse")
    print("=" * 70)
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("CREATE DATABASE IF NOT EXISTS f1_datawarehouse")
        cursor.execute("USE f1_datawarehouse")
        
        print("✅ Base de datos 'f1_datawarehouse' lista para usar")
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print("❌ Error al crear base de datos:")
        print(f"   {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "VERIFICACIÓN DE CONEXIÓN MYSQL" + " " * 23 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    # Ejecutar tests
    test1 = test_conexion()
    
    if test1:
        test2 = test_crear_database()
        
        if test2:
            test3 = test_crear_f1_database()
            
            if test3:
                print("\n" + "=" * 70)
                print("🎉 TODOS LOS TESTS PASARON - Puedes ejecutar el ETL")
                print("=" * 70)
                print("\n▶️  Ejecuta: python etl.py\n")
                return
    
    print("\n" + "=" * 70)
    print("⚠️  TESTS FALLARON - Corrige los errores antes de ejecutar el ETL")
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()
