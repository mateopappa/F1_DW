# 🚀 Guía de Despliegue del Dashboard F1

## Opción 1: Streamlit Community Cloud (Recomendado - GRATIS)

### Prerrequisitos
- ✅ Cuenta de GitHub (ya tienes)
- ✅ Repositorio público (F1_DW - ya está)
- ⚠️ **Necesitas una base de datos MySQL accesible desde internet**

### 🔴 IMPORTANTE: Base de Datos
Streamlit Cloud NO incluye hosting de base de datos MySQL. Tienes 3 opciones:

#### **Opción A: Base de Datos MySQL en la Nube (Recomendada)**

**Servicios gratuitos/económicos:**

1. **PlanetScale (MySQL Compatible - GRATIS)**
   - URL: https://planetscale.com/
   - Plan gratuito: 1 base de datos, 5GB storage
   - Serverless, fácil de usar
   - **Recomendación:** ⭐⭐⭐⭐⭐

2. **Railway (GRATIS hasta $5/mes de uso)**
   - URL: https://railway.app/
   - MySQL incluido
   - $5 de crédito gratis al mes
   - **Recomendación:** ⭐⭐⭐⭐

3. **AWS RDS Free Tier (12 meses gratis)**
   - URL: https://aws.amazon.com/rds/free/
   - MySQL 5.7/8.0
   - Requiere cuenta AWS
   - **Recomendación:** ⭐⭐⭐

4. **Google Cloud SQL (Prueba gratis $300)**
   - URL: https://cloud.google.com/sql
   - MySQL 8.0
   - $300 de crédito por 90 días
   - **Recomendación:** ⭐⭐⭐

#### **Opción B: SQLite (Más Simple)**
Convertir el proyecto a SQLite (no requiere servidor):
- Ventaja: Todo en un archivo .db
- Desventaja: Menos potente que MySQL
- Ideal para: Proyectos pequeños

#### **Opción C: Datos Estáticos (Solo Lectura)**
Exportar datos a CSV y cargar desde archivos:
- Ventaja: Sin base de datos externa
- Desventaja: Sin actualizaciones en tiempo real
- Ideal para: Demostración

### Pasos para Desplegar en Streamlit Cloud

1. **Ir a Streamlit Cloud**
   - URL: https://share.streamlit.io/
   - Click en "Sign in with GitHub"
   - Autorizar acceso a tus repositorios

2. **Crear Nueva App**
   - Click en "New app"
   - Selecciona:
     - Repository: `mateopappa/F1_DW`
     - Branch: `v2_dashboard_on_python`
     - Main file path: `dashboard.py`
   - Click "Deploy!"

3. **Configurar Secrets (IMPORTANTE)**
   - En el dashboard de tu app, ve a "Settings" > "Secrets"
   - Pega esto (con TUS credenciales de base de datos en la nube):
   
   ```toml
   [mysql]
   host = "TU_HOST_MYSQL_EN_LA_NUBE"
   port = 3306
   database = "f1_datawarehouse"
   user = "TU_USUARIO"
   password = "TU_PASSWORD"
   ```

4. **Esperar el Deploy**
   - Streamlit Cloud instalará las dependencias
   - Mostrará logs en tiempo real
   - Tarda ~2-5 minutos

5. **¡Listo!**
   - Tu app estará en: `https://NOMBRE-APP.streamlit.app`
   - Puedes compartir la URL con cualquiera

---

## Opción 2: Despliegue en Servidor Propio

### A. Heroku (Pago - $7/mes)
- Antes era gratis, ahora de pago
- Fácil de usar
- Incluye add-ons para MySQL

### B. DigitalOcean App Platform ($5/mes)
- Droplet básico
- Configuras servidor Linux
- Instalas MySQL + Python

### C. Railway ($5/mes de crédito gratis)
- Similar a Heroku
- Muy fácil de usar
- Incluye base de datos

---

## 📋 Checklist Pre-Despliegue

- [ ] Base de datos MySQL accesible desde internet configurada
- [ ] Datos cargados en la base de datos (ejecutar ETL)
- [ ] `requirements.txt` actualizado
- [ ] `.streamlit/config.toml` creado
- [ ] Secrets configurados en Streamlit Cloud
- [ ] Repository pusheado a GitHub

---

## 🔧 Solución de Problemas

### Error: "Connection refused"
- Verifica que la base de datos acepte conexiones externas
- Revisa el firewall de tu proveedor de base de datos
- Confirma que los secrets estén bien configurados

### Error: "Module not found"
- Verifica que todas las dependencias estén en `requirements.txt`
- Reinicia el deploy desde el dashboard de Streamlit Cloud

### La app es lenta
- Considera agregar más `@st.cache_data` decorators
- Optimiza las queries SQL
- Usa índices en la base de datos

---

## 💡 Recomendación Final

**Para este proyecto, te recomiendo:**

1. **Crear cuenta en PlanetScale** (gratis, serverless MySQL)
2. **Importar tu base de datos** (exportar desde local, importar a PlanetScale)
3. **Desplegar en Streamlit Cloud** (gratis también)
4. **Resultado:** Dashboard 100% gratis en internet 🎉

**Costo total:** $0/mes  
**Tiempo estimado:** 30-45 minutos  
**Dificultad:** Media

---

## 📞 Soporte

Si necesitas ayuda:
- Streamlit Docs: https://docs.streamlit.io/streamlit-community-cloud
- Community Forum: https://discuss.streamlit.io/
- PlanetScale Docs: https://planetscale.com/docs
