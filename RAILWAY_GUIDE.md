# 🚂 Guía de Despliegue en Railway

## 📋 Pasos para Desplegar

### 1️⃣ Crear Cuenta en Railway

1. Ir a https://railway.app/
2. Click en "Start a New Project"
3. Login con GitHub (recomendado)
4. Verificar email si es necesario

### 2️⃣ Crear Base de Datos MySQL

1. En Railway dashboard, click "New Project"
2. Seleccionar "Provision MySQL"
3. Esperar a que se cree (~30 segundos)
4. Click en el servicio MySQL
5. Ir a "Variables" tab
6. **Copiar estas variables (las necesitarás):**
   - `MYSQL_HOST` (ejemplo: containers-us-west-xxx.railway.app)
   - `MYSQL_PORT` (ejemplo: 6379)
   - `MYSQL_DATABASE` (ejemplo: railway)
   - `MYSQL_USER` (ejemplo: root)
   - `MYSQL_PASSWORD` (ejemplo: randompassword123)

### 3️⃣ Importar Datos a MySQL de Railway

**Opción A: Desde tu MySQL Local**

```bash
# 1. Exportar datos locales
mysqldump -u root f1_datawarehouse > f1_backup.sql

# 2. Importar a Railway (usa las credenciales que copiaste)
mysql -h MYSQL_HOST -P MYSQL_PORT -u MYSQL_USER -p MYSQL_DATABASE < f1_backup.sql
# Te pedirá el password (pega MYSQL_PASSWORD)

# 3. Verificar que se importó
mysql -h MYSQL_HOST -P MYSQL_PORT -u MYSQL_USER -p MYSQL_DATABASE -e "SHOW TABLES;"
```

**Opción B: Ejecutar el ETL directamente contra Railway**

```bash
# Modificar temporalmente etl.py con las credenciales de Railway
# Luego ejecutar:
python3 etl.py
```

### 4️⃣ Desplegar el Dashboard

**Opción A: Desde GitHub (Recomendado)**

1. En Railway, click "New Project"
2. Seleccionar "Deploy from GitHub repo"
3. Autorizar acceso a tu cuenta de GitHub
4. Seleccionar el repo `F1_DW`
5. Seleccionar la rama `v2_dashboard_on_python`
6. Railway detectará automáticamente el Dockerfile
7. Click "Deploy"

**Opción B: Desde CLI de Railway**

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Crear nuevo proyecto
railway init

# Deploy
railway up
```

### 5️⃣ Configurar Variables de Entorno

1. En Railway dashboard, click en tu servicio del Dashboard
2. Ir a "Variables" tab
3. Agregar las siguientes variables (usa los valores del MySQL que creaste):

```
MYSQL_HOST=containers-us-west-xxx.railway.app
MYSQL_PORT=6379
MYSQL_DATABASE=railway
MYSQL_USER=root
MYSQL_PASSWORD=tu_password_aqui
```

4. Click "Deploy" (se reiniciará automáticamente)

### 6️⃣ Configurar Dominio Público

1. En Railway dashboard, click en tu servicio del Dashboard
2. Ir a "Settings" tab
3. En "Networking", click "Generate Domain"
4. Railway te dará una URL pública: `https://tu-app.up.railway.app`
5. ¡Listo! Comparte esa URL

---

## 🐳 Probar Localmente con Docker (Opcional)

Antes de deployar, puedes probar todo localmente:

```bash
# 1. Crear archivo .env (copia de .env.example)
cp .env.example .env

# 2. Ajustar valores en .env si es necesario

# 3. Levantar todo (MySQL + Dashboard)
docker-compose up -d

# 4. Ver logs
docker-compose logs -f dashboard

# 5. Acceder a:
# - Dashboard: http://localhost:8501
# - MySQL: localhost:3306

# 6. Cargar datos (solo primera vez)
# Opción A: Importar backup
docker exec -i f1_mysql mysql -u f1user -pf1_password f1_datawarehouse < f1_backup.sql

# Opción B: Ejecutar ETL
# (Modifica etl.py para usar host='localhost', user='f1user', password='f1_password')
python3 etl.py

# 7. Detener todo
docker-compose down

# 8. Detener y eliminar datos
docker-compose down -v
```

---

## 💰 Costos Estimados

**Plan Hobby (Gratis):**
- ✅ $5 USD de crédito gratis cada mes
- ✅ Se renueva mensualmente
- ✅ Para tu proyecto: ~$2-3/mes de uso real
- ✅ **Resultado: Gratis indefinidamente**

**Uso estimado de tu proyecto:**
- MySQL pequeño: ~$1.50/mes
- Dashboard (512MB RAM): ~$1.00/mes
- **Total:** ~$2.50/mes (dentro de los $5 gratis)

**¿Qué pasa si me paso de $5?**
- Te envían un email de advertencia
- Puedes agregar tarjeta de crédito
- O pausar el proyecto hasta el siguiente mes

---

## 🔧 Solución de Problemas

### Error: "Application failed to respond"

**Causa:** El dashboard no está escuchando en el puerto correcto.

**Solución:** Verifica que el Dockerfile tenga:
```dockerfile
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### Error: "Can't connect to MySQL server"

**Causa:** Variables de entorno mal configuradas.

**Solución:**
1. Verifica las variables en Railway
2. Asegúrate de que sean exactamente las del servicio MySQL
3. Reinicia el servicio del Dashboard

### Error: "No tables found"

**Causa:** Los datos no se importaron.

**Solución:**
1. Importa el backup SQL
2. O ejecuta el ETL apuntando a Railway

### La app es muy lenta

**Causa:** Tier gratuito tiene recursos limitados.

**Soluciones:**
- Optimiza las queries con `@st.cache_data`
- Usa índices en MySQL
- Considera agregar más RAM (cuesta más)

---

## 📊 Monitoreo

**Ver logs en tiempo real:**
```bash
railway logs
```

**Ver métricas:**
1. Railway dashboard → Tu servicio
2. "Metrics" tab
3. Verás: CPU, RAM, Network

**Ver cuánto gastaste:**
1. Railway dashboard → Settings
2. "Usage" tab
3. Verás: $X.XX / $5.00 este mes

---

## 🔄 Actualizar el Dashboard

Cada vez que hagas `git push` a la rama `v2_dashboard_on_python`:
1. Railway detecta el cambio automáticamente
2. Rebuild del Docker image
3. Redeploy automático (~2-3 minutos)

**No necesitas hacer nada manual** 🎉

---

## 🎯 Checklist Final

- [ ] Cuenta creada en Railway
- [ ] MySQL provisionado
- [ ] Datos importados (verificado con SHOW TABLES)
- [ ] Dashboard desplegado desde GitHub
- [ ] Variables de entorno configuradas
- [ ] Dominio público generado
- [ ] App funcionando (abre la URL y prueba)
- [ ] Compartir URL con el mundo 🚀

---

## 🆘 Ayuda

- Docs oficiales: https://docs.railway.app/
- Discord de Railway: https://discord.gg/railway
- Status: https://railway.statuspage.io/

¡Éxito con el deploy! 🏎️✨
