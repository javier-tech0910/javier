# VIBRA — publicación en Internet

Esta versión mantiene la misma estructura de carpetas del proyecto.

## 1. Probar localmente

Instala dependencias:

```powershell
pip install -r requirements.txt
```

Inicia:

```powershell
python app.py
```

## 2. Subir a GitHub

Crea un repositorio nuevo y sube **el contenido de esta carpeta**, incluyendo `app.py`, `templates`, `static`, `requirements.txt`, `Procfile` y `schema_nuevo.sql`.

No subas `.env` ni contraseñas.

## 3. Railway

Crea un proyecto nuevo en Railway y conecta el repositorio de GitHub.

Añade un servicio MySQL desde Railway.

Configura en el servicio web estas variables:

```text
MYSQL_HOST=<host de MySQL de Railway>
MYSQL_PORT=<puerto de MySQL>
MYSQL_USER=<usuario de MySQL>
MYSQL_PASSWORD=<contraseña de MySQL>
MYSQL_DATABASE=<base de datos>
VIBRA_SECRET_KEY=<cadena larga y aleatoria>
VIBRA_UPLOAD_FOLDER=/app/data/uploads
VIBRA_MUSIC_FOLDER=/app/data/music
```

Si Railway te proporciona `MYSQL_URL`, también puedes usar los datos equivalentes del servicio MySQL, pero esta versión de VIBRA espera las variables separadas anteriores.

## 4. Comando de inicio

El `Procfile` ya contiene:

```text
web: gunicorn app:app
```

Por eso Railway puede iniciar Flask con Gunicorn.

## 5. Base de datos

Importa `schema_nuevo.sql` en la base de datos MySQL de Railway.

**No ejecutes `upgrade_vibra.sql` si estás creando la base desde cero.**

## 6. URL pública

En Railway entra al servicio web → Networking → Generate Domain.

Railway te entregará una dirección pública `.railway.app`.

## 7. Archivos multimedia

La aplicación actual guarda imágenes y videos en `uploads/` y música en `music/`.

Para producción, estos archivos necesitan almacenamiento persistente. Crea **un solo volumen** para el servicio web y monta el volumen en:

```text
/app/data
```

Luego usa estas variables del servicio web:

```text
VIBRA_UPLOAD_FOLDER=/app/data/uploads
VIBRA_MUSIC_FOLDER=/app/data/music
```

Así imágenes, videos y música quedan dentro del mismo volumen persistente. Railway documenta que cada servicio puede tener un solo volumen. Para una red social grande, más adelante conviene migrar multimedia a almacenamiento de objetos.
