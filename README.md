# VIBRA — base completa

Red social local en Flask + MySQL con identidad rojo/negro.

## Incluye
- Registro, login, sesiones y perfiles.
- Feed mixto de imágenes y videos.
- Música adjunta a publicaciones.
- Likes, comentarios, seguidores y notificaciones.
- Historias con vencimiento.
- Guardados.
- Búsqueda de usuarios, publicaciones y hashtags.
- Perfil propio y perfiles públicos.
- Crear/editar publicaciones.
- Mensajes básicos.
- Configuración y enlace de apoyo/monetización.
- Área de creador con estadísticas y botón de apoyo.
- PWA básica (manifest + service worker).
- Diseño responsive rojo/negro inspirado en redes sociales, pero con identidad VIBRA.

## Instalación
1. Copia esta carpeta en tu PC.
2. Crea/usa tu base `vibra`.
3. Ejecuta `upgrade_vibra.sql` en MySQL Workbench.
4. Instala:
   `python -m pip install flask mysql-connector-python werkzeug requests`
5. Si quieres pagos, copia `.env.example` como `.env` y coloca tu token de Mercado Pago.
6. Ejecuta `python app.py`.
7. Abre `http://127.0.0.1:5000`.

## Música y derechos
Sube únicamente música que tengas derecho a usar. La aplicación no incluye canciones comerciales con copyright.

## Monetización
Sin credenciales de pago, VIBRA muestra el sistema de apoyo pero no procesa dinero. Con Mercado Pago configurado, la ruta `/apoyar/<usuario_id>` crea un checkout. La API actual de Mercado Pago usa un Access Token y permite crear un checkout mediante su API; para una integración nueva Mercado Pago recomienda su flujo Orders/Checkout Pro moderno. Revisa sus requisitos de cuenta y cumplimiento antes de publicar cobros reales.
