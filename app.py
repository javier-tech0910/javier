from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory, jsonify, flash
import mysql.connector
import boto3
import os, uuid, re
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

load_dotenv()

S3_ENDPOINT_URL = os.getenv('S3_ENDPOINT_URL')
S3_REGION = os.getenv('S3_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
S3_ACCESS_KEY_ID = os.getenv('S3_ACCESS_KEY_ID')
S3_SECRET_ACCESS_KEY = os.getenv('S3_SECRET_ACCESS_KEY')

s3 = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT_URL,
    region_name=S3_REGION,
    aws_access_key_id=S3_ACCESS_KEY_ID,
    aws_secret_access_key=S3_SECRET_ACCESS_KEY
)


app = Flask(__name__)
csrf = CSRFProtect(app)
@app.context_processor
def csrf_token():
    from flask_wtf.csrf import generate_csrf
    return {'csrf_token': generate_csrf}
app.secret_key = os.getenv('VIBRA_SECRET_KEY', 'vibra-dev-change-me')
BASE = os.path.dirname(os.path.abspath(__file__))
# En local se mantienen las carpetas actuales. En producción Railway puede
# sobrescribir estas rutas con un único volumen persistente.
UPLOAD_FOLDER = os.getenv('VIBRA_UPLOAD_FOLDER', os.path.join(BASE, 'uploads'))
MUSIC_FOLDER = os.getenv('VIBRA_MUSIC_FOLDER', os.path.join(BASE, 'music'))
os.makedirs(UPLOAD_FOLDER, exist_ok=True); os.makedirs(MUSIC_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSIC_FOLDER'] = MUSIC_FOLDER
ALLOWED_IMAGES={'png','jpg','jpeg','gif','webp'}; ALLOWED_VIDEOS={'mp4','webm','mov','m4v'}; ALLOWED_AUDIO={'mp3','wav','ogg','m4a'}

def db():
    return mysql.connector.connect(host=os.getenv('MYSQL_HOST','localhost'), user=os.getenv('MYSQL_USER','vibra_app'), password=os.getenv('MYSQL_PASSWORD','Vibra1234'), database=os.getenv('MYSQL_DATABASE','vibra'))

def ext_ok(filename, allowed): return '.' in filename and filename.rsplit('.',1)[1].lower() in allowed

def save_file(file, folder, allowed):
    if not file or not file.filename or not ext_ok(file.filename, allowed): return None
    ext=file.filename.rsplit('.',1)[1].lower(); name=f'{uuid.uuid4().hex}.{ext}'; file.save(os.path.join(folder,name)); return name

def save_image_to_bucket(file, folder_name):
    if not file or not file.filename or not ext_ok(file.filename, ALLOWED_IMAGES):
        return None

    ext = file.filename.rsplit('.', 1)[1].lower()
    key = f"{folder_name}/{uuid.uuid4().hex}.{ext}"

    try:
        s3.upload_fileobj(
            file,
            S3_BUCKET_NAME,
            key,
            ExtraArgs={
                'ContentType': file.content_type or 'image/jpeg'
            }
        )
        return key
    except Exception as e:
        print('Error subiendo imagen al Bucket:', e)
        return None

def current_user():
    if 'usuario_id' not in session: return None
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT * FROM usuarios WHERE id=%s',(session['usuario_id'],)); u=cur.fetchone(); cur.close(); c.close(); return u

def notify(user_id, actor_id, tipo, texto, publicacion_id=None):
    if not user_id or user_id==actor_id: return
    c=db(); cur=c.cursor(); cur.execute('INSERT INTO notificaciones(usuario_id,actor_id,tipo,texto,publicacion_id) VALUES(%s,%s,%s,%s,%s)',(user_id,actor_id,tipo,texto,publicacion_id)); c.commit(); cur.close(); c.close()

def feed_rows(uid):
    c=db(); cur=c.cursor(dictionary=True)
    cur.execute('''SELECT p.*,u.nombre,u.username,u.foto_perfil,COALESCE(l.cantidad,0) cantidad_likes,CASE WHEN ul.id IS NULL THEN 0 ELSE 1 END usuario_dio_like,CASE WHEN g.id IS NULL THEN 0 ELSE 1 END guardado,c.titulo musica_titulo,c.artista musica_artista,c.archivo musica_archivo FROM publicaciones p JOIN usuarios u ON u.id=p.usuario_id LEFT JOIN (SELECT publicacion_id,COUNT(*) cantidad FROM likes GROUP BY publicacion_id) l ON l.publicacion_id=p.id LEFT JOIN likes ul ON ul.publicacion_id=p.id AND ul.usuario_id=%s LEFT JOIN guardados g ON g.publicacion_id=p.id AND g.usuario_id=%s LEFT JOIN canciones c ON c.id=p.musica_id ORDER BY p.fecha DESC LIMIT 80''',(uid,uid)); posts=cur.fetchall()
    for p in posts:
        cur.execute('SELECT co.id,co.comentario,co.fecha,u.nombre,u.username,u.foto_perfil FROM comentarios co JOIN usuarios u ON u.id=co.usuario_id WHERE co.publicacion_id=%s ORDER BY co.fecha ASC',(p['id'],)); p['comentarios']=cur.fetchall()
    cur.execute('SELECT h.*,u.nombre,u.username,u.foto_perfil FROM historias h JOIN usuarios u ON u.id=h.usuario_id WHERE h.expira>NOW() ORDER BY h.fecha DESC LIMIT 30'); stories=cur.fetchall()
    cur.close(); c.close(); return posts,stories

@app.context_processor
def inject():
    u=current_user() if 'usuario_id' in session else None
    unread=0
    if u:
        c=db(); cur=c.cursor(); cur.execute('SELECT COUNT(*) FROM notificaciones WHERE usuario_id=%s AND leida=0',(u['id'],)); unread=cur.fetchone()[0]; cur.close(); c.close()
    return {'yo':u,'notificaciones_no_leidas':unread}

@app.route('/')
def inicio():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    posts,stories=feed_rows(session['usuario_id']); return render_template('index.html',publicaciones=posts,historias=stories)

@app.route('/registro',methods=['GET','POST'])
def registro():
    if request.method=='POST':
        nombre=request.form.get('nombre','').strip(); email=request.form.get('email','').strip().lower(); password=request.form.get('contraseña',''); username=request.form.get('username','').strip().lower()
        username=re.sub(r'[^a-z0-9_.-]','',username)[:50]
        if not nombre or not email or not password: flash('Completa todos los campos.','error'); return render_template('registro.html')
        if not username: username=re.sub(r'[^a-z0-9_.-]','_',nombre.lower())[:50]
        c=db(); cur=c.cursor()
        try:
            cur.execute('INSERT INTO usuarios(nombre,username,email,contraseña) VALUES(%s,%s,%s,%s)',(nombre,username,email,generate_password_hash(password))); c.commit()
        except mysql.connector.IntegrityError: c.rollback(); flash('El correo o nombre de usuario ya existe.','error'); cur.close(); c.close(); return render_template('registro.html')
        cur.close(); c.close(); return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('contraseña',''); c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT * FROM usuarios WHERE email=%s',(email,)); u=cur.fetchone(); cur.close(); c.close()
        if not u or not check_password_hash(u['contraseña'],password): flash('Correo o contraseña incorrectos.','error'); return render_template('login.html')
        session['usuario_id']=u['id']; session['usuario_nombre']=u['nombre']; return redirect(url_for('inicio'))
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    return redirect(url_for('perfil_usuario',usuario_id=session['usuario_id']))

@app.route('/perfil/<int:usuario_id>')
def perfil_usuario(usuario_id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT * FROM usuarios WHERE id=%s',(usuario_id,)); u=cur.fetchone()
    if not u: cur.close(); c.close(); return 'Usuario no encontrado',404
    cur.execute('SELECT COUNT(*) cantidad FROM publicaciones WHERE usuario_id=%s',(usuario_id,)); u['cantidad_publicaciones']=cur.fetchone()['cantidad']
    cur.execute('SELECT COUNT(*) cantidad FROM seguidores WHERE seguido_id=%s',(usuario_id,)); u['seguidores']=cur.fetchone()['cantidad']
    cur.execute('SELECT COUNT(*) cantidad FROM seguidores WHERE seguidor_id=%s',(usuario_id,)); u['siguiendo_count']=cur.fetchone()['cantidad']
    cur.execute('SELECT id FROM seguidores WHERE seguidor_id=%s AND seguido_id=%s',(session['usuario_id'],usuario_id)); siguiendo=cur.fetchone() is not None
    cur.execute('SELECT p.*,c.titulo musica_titulo,c.artista musica_artista FROM publicaciones p LEFT JOIN canciones c ON c.id=p.musica_id WHERE p.usuario_id=%s ORDER BY p.fecha DESC',(usuario_id,)); posts=cur.fetchall(); cur.close(); c.close()
    return render_template('perfil_usuario.html',usuario=u,publicaciones=posts,siguiendo=siguiendo)

@app.route('/editar-perfil', methods=['GET', 'POST'])
def editar_perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        username = request.form.get('username', '').strip().lower()
        desc = request.form.get('descripcion', '').strip()
        apoyo = request.form.get('link_apoyo', '').strip()

        portada = save_image_to_bucket(
            request.files.get('foto_portada'),
            'covers'
        )

        avatar = save_image_to_bucket(
            request.files.get('foto_perfil'),
            'profiles'
        )



        c = db()
        cur = c.cursor()

        fields = [
            'nombre=%s',
            'username=%s',
            'descripcion=%s',
            'link_apoyo=%s'
        ]

        vals = [
            nombre,
            username,
            desc,
            apoyo
        ]

        if portada:
            fields.append('foto_portada=%s')
            vals.append(portada)

        if avatar:
            fields.append('foto_perfil=%s')
            vals.append(avatar)

        vals.append(session['usuario_id'])

        try:
            sql = 'UPDATE usuarios SET ' + ','.join(fields) + ' WHERE id=%s'



            cur.execute(sql, vals)



            c.commit()



            flash('Perfil actualizado.', 'ok')

        except mysql.connector.Error as e:
            c.rollback()

            print("ERROR MYSQL:", e)

            flash(
                'No se pudo guardar. Revisa que el usuario no esté ocupado.',
                'error'
            )

        finally:
            cur.close()
            c.close()

        return redirect(url_for('perfil'))

    return render_template(
        'editar_perfil.html',
        usuario=current_user()
    )

@app.route('/api/video-upload-url', methods=['POST'])
def video_upload_url():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    filename = data.get('filename', '')
    content_type = data.get('content_type', 'video/mp4')

    if not filename:
        return jsonify({'error': 'Falta el nombre del archivo'}), 400

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext not in ALLOWED_VIDEOS:
        return jsonify({'error': 'Formato de video no permitido'}), 400

    key = f"videos/{session['usuario_id']}/{uuid.uuid4().hex}.{ext}"

    try:
        url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': key,
                'ContentType': content_type
            },
            ExpiresIn=600,
            HttpMethod='PUT'
        )

        return jsonify({
            'url': url,
            'key': key
        })

    except Exception as e:
        print('Error generando URL S3:', e)
        return jsonify({'error': 'No se pudo preparar la subida'}), 500

@app.route('/crear-publicacion',methods=['GET','POST'])
def crear_publicacion():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT * FROM canciones ORDER BY fecha DESC'); canciones=cur.fetchall(); cur.close(); c.close()
    if request.method=='POST':
       imagen=request.files.get('imagen'); video=request.files.get('video'); video_key=request.form.get('video_key')
       if video_key:
           prefijo_video = f"videos/{session['usuario_id']}/"
           if not video_key.startswith(prefijo_video):
               flash('Video no válido.', 'error')
               return render_template('crear_publicacion.html', canciones=canciones)

       tipo='video' if video_key or (video and video.filename) else 'imagen'
       img=save_image_to_bucket(imagen,'images')
       vid=video_key or save_file(video,UPLOAD_FOLDER,ALLOWED_VIDEOS)
       desc=request.form.get('descripcion','').strip()
       ubic=request.form.get('ubicacion','').strip()
       hashtags=request.form.get('hashtags','').strip()
       musica=request.form.get('musica_id') or None

       if tipo=='imagen' and not img:
           flash('Selecciona una imagen.','error')
           return render_template('crear_publicacion.html',canciones=canciones)

       if tipo=='video' and not vid:
           flash('Video no válido. Usa MP4, WEBM o MOV.','error')
           return render_template('crear_publicacion.html',canciones=canciones)

       c=db()
       cur=c.cursor()
       cur.execute(
           'INSERT INTO publicaciones(usuario_id,imagen,video,tipo,descripcion,ubicacion,hashtags,musica_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
           (session['usuario_id'],img,vid,tipo,desc,ubic,hashtags,musica)
       )
       c.commit()
       cur.close()
       c.close()
       return redirect(url_for('inicio'))

    return render_template('crear_publicacion.html',canciones=canciones)

@app.route('/api/video-delete-upload', methods=['POST'])
def video_delete_upload():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    key = data.get('key', '')

    usuario_id = str(session['usuario_id'])
    prefijo = f"videos/{usuario_id}/"

    # Solo permitimos borrar videos temporales del usuario actual.
    if not key.startswith(prefijo):
        return jsonify({'error': 'Archivo no permitido'}), 403

    try:
        s3.delete_object(
            Bucket=S3_BUCKET_NAME,
            Key=key
        )
        return jsonify({'ok': True})

    except Exception as e:
        print('Error eliminando video temporal:', e)
        return jsonify({'error': 'No se pudo eliminar el video'}), 500

@app.route('/publicacion/<int:publicacion_id>')
def ver_publicacion(publicacion_id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT p.*,u.nombre,u.username,u.foto_perfil,c.titulo musica_titulo,c.artista musica_artista,c.archivo musica_archivo FROM publicaciones p JOIN usuarios u ON u.id=p.usuario_id LEFT JOIN canciones c ON c.id=p.musica_id WHERE p.id=%s',(publicacion_id,)); p=cur.fetchone()
    if not p: cur.close(); c.close(); return 'Publicación no encontrada',404
    cur.execute('SELECT COUNT(*) cantidad FROM likes WHERE publicacion_id=%s',(publicacion_id,)); p['cantidad_likes']=cur.fetchone()['cantidad']; cur.execute('SELECT id FROM likes WHERE publicacion_id=%s AND usuario_id=%s',(publicacion_id,session['usuario_id'])); p['usuario_dio_like']=bool(cur.fetchone()); cur.execute('SELECT co.*,u.nombre,u.username,u.foto_perfil FROM comentarios co JOIN usuarios u ON u.id=co.usuario_id WHERE co.publicacion_id=%s ORDER BY co.fecha',(publicacion_id,)); p['comentarios']=cur.fetchall(); cur.close(); c.close(); return render_template('ver_publicacion.html',publicacion=p)

@app.route('/buscar')
def buscar():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    q=request.args.get('q','').strip(); users=[]; posts=[]; c=db(); cur=c.cursor(dictionary=True)
    if q:
        like='%'+q+'%'; cur.execute('SELECT id,nombre,username,descripcion,foto_perfil FROM usuarios WHERE nombre LIKE %s OR username LIKE %s ORDER BY nombre LIMIT 30',(like,like)); users=cur.fetchall(); cur.execute('SELECT p.*,u.nombre,u.username,u.foto_perfil FROM publicaciones p JOIN usuarios u ON u.id=p.usuario_id WHERE p.descripcion LIKE %s OR p.hashtags LIKE %s ORDER BY p.fecha DESC LIMIT 30',(like,like)); posts=cur.fetchall()
    cur.close(); c.close(); return render_template('buscar.html',usuarios=users,publicaciones=posts,busqueda=q)

@app.route('/like/<int:publicacion_id>',methods=['POST'])
def like(publicacion_id):
    if 'usuario_id' not in session: return jsonify(error='login'),401
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT id,usuario_id FROM publicaciones WHERE id=%s',(publicacion_id,)); p=cur.fetchone()
    if not p: cur.close(); c.close(); return jsonify(error='not found'),404
    cur.execute('SELECT id FROM likes WHERE usuario_id=%s AND publicacion_id=%s',(session['usuario_id'],publicacion_id)); row=cur.fetchone()
    if row: cur.execute('DELETE FROM likes WHERE id=%s',(row['id'],)); liked=False
    else: cur.execute('INSERT INTO likes(usuario_id,publicacion_id) VALUES(%s,%s)',(session['usuario_id'],publicacion_id)); liked=True
    c.commit(); cur.execute('SELECT COUNT(*) cantidad FROM likes WHERE publicacion_id=%s',(publicacion_id,)); n=cur.fetchone()['cantidad']; cur.close(); c.close();
    if liked: notify(p['usuario_id'],session['usuario_id'],'like','Le dio me gusta a tu publicación.',publicacion_id)
    return jsonify(liked=liked,likes=n)

@app.route('/guardar/<int:publicacion_id>',methods=['POST'])
def guardar(publicacion_id):
    if 'usuario_id' not in session: return jsonify(error='login'),401
    c=db(); cur=c.cursor(); cur.execute('SELECT id FROM guardados WHERE usuario_id=%s AND publicacion_id=%s',(session['usuario_id'],publicacion_id)); row=cur.fetchone()
    if row: cur.execute('DELETE FROM guardados WHERE id=%s',(row[0],)); saved=False
    else: cur.execute('INSERT INTO guardados(usuario_id,publicacion_id) VALUES(%s,%s)',(session['usuario_id'],publicacion_id)); saved=True
    c.commit(); cur.close(); c.close(); return jsonify(saved=saved)

@app.route('/comentario/<int:publicacion_id>',methods=['POST'])
def comentario(publicacion_id):
    if 'usuario_id' not in session: return jsonify(error='login'),401
    data=request.get_json(silent=True) or {}; texto=data.get('comentario','').strip()
    if not texto: return jsonify(error='vacío'),400
    c=db(); cur=c.cursor(dictionary=True); cur.execute('INSERT INTO comentarios(usuario_id,publicacion_id,comentario) VALUES(%s,%s,%s)',(session['usuario_id'],publicacion_id,texto)); c.commit(); cur.execute('SELECT nombre,username,foto_perfil FROM usuarios WHERE id=%s',(session['usuario_id'],)); u=cur.fetchone(); cur.execute('SELECT usuario_id FROM publicaciones WHERE id=%s',(publicacion_id,)); p=cur.fetchone(); cur.close(); c.close(); notify(p['usuario_id'],session['usuario_id'],'comentario','Comentó tu publicación.',publicacion_id); return jsonify(nombre=u['nombre'],username=u['username'],foto_perfil=u['foto_perfil'],comentario=texto,fecha=datetime.now().strftime('%d/%m/%Y %H:%M'))

@app.route('/seguir/<int:usuario_id>',methods=['POST'])
def seguir(usuario_id):
    if 'usuario_id' not in session: return jsonify(error='login'),401
    if usuario_id==session['usuario_id']: return jsonify(error='No puedes seguirte'),400
    c=db(); cur=c.cursor(); cur.execute('SELECT id FROM seguidores WHERE seguidor_id=%s AND seguido_id=%s',(session['usuario_id'],usuario_id)); row=cur.fetchone()
    if row: cur.execute('DELETE FROM seguidores WHERE id=%s',(row[0],)); following=False
    else: cur.execute('INSERT INTO seguidores(seguidor_id,seguido_id) VALUES(%s,%s)',(session['usuario_id'],usuario_id)); following=True
    c.commit(); cur.execute('SELECT COUNT(*) FROM seguidores WHERE seguido_id=%s',(usuario_id,)); n=cur.fetchone()[0]; cur.close(); c.close();
    if following: notify(usuario_id,session['usuario_id'],'seguidor','Empezó a seguirte.')
    return jsonify(siguiendo=following,seguidores=n)

@app.route('/notificaciones')
def notificaciones():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT n.*,u.nombre,u.username,u.foto_perfil FROM notificaciones n LEFT JOIN usuarios u ON u.id=n.actor_id WHERE n.usuario_id=%s ORDER BY n.fecha DESC LIMIT 100',(session['usuario_id'],)); rows=cur.fetchall(); cur.execute('UPDATE notificaciones SET leida=1 WHERE usuario_id=%s',(session['usuario_id'],)); c.commit(); cur.close(); c.close(); return render_template('notificaciones.html',notificaciones=rows)

@app.route('/guardados')
def guardados():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT p.*,u.nombre,u.username,u.foto_perfil FROM guardados g JOIN publicaciones p ON p.id=g.publicacion_id JOIN usuarios u ON u.id=p.usuario_id WHERE g.usuario_id=%s ORDER BY g.fecha DESC',(session['usuario_id'],)); posts=cur.fetchall(); cur.close(); c.close(); return render_template('guardados.html',publicaciones=posts)

@app.route('/historias/crear',methods=['GET','POST'])
def crear_historia():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method=='POST':
        f=request.files.get('archivo'); img=save_image_to_bucket(f,'stories'); vid=save_file(f,UPLOAD_FOLDER,ALLOWED_VIDEOS) if not img else None; archivo=img or vid
        if not archivo: flash('Archivo no válido.','error'); return render_template('crear_historia.html')
        tipo='video' if vid else 'imagen'; texto=request.form.get('texto','').strip(); c=db(); cur=c.cursor(); cur.execute('INSERT INTO historias(usuario_id,archivo,tipo,texto,expira) VALUES(%s,%s,%s,%s,%s)',(session['usuario_id'],archivo,tipo,texto,datetime.now()+timedelta(hours=24))); c.commit(); cur.close(); c.close(); return redirect(url_for('inicio'))
    return render_template('crear_historia.html')

@app.route('/musica')
def musica():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT c.*,u.nombre FROM canciones c LEFT JOIN usuarios u ON u.id=c.usuario_id ORDER BY c.fecha DESC'); rows=cur.fetchall(); cur.close(); c.close(); return render_template('musica.html',canciones=rows)

@app.route('/musica/subir',methods=['POST'])
def subir_musica():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    f=request.files.get('archivo'); filename=save_file(f,MUSIC_FOLDER,ALLOWED_AUDIO)
    if not filename: flash('Audio no válido.','error'); return redirect(url_for('musica'))
    titulo=request.form.get('titulo','Sin título').strip(); artista=request.form.get('artista','Artista VIBRA').strip(); c=db(); cur=c.cursor(); cur.execute('INSERT INTO canciones(titulo,artista,archivo,usuario_id) VALUES(%s,%s,%s,%s)',(titulo,artista,filename,session['usuario_id'])); c.commit(); cur.close(); c.close(); return redirect(url_for('musica'))

@app.route('/apoyar/<int:usuario_id>',methods=['GET','POST'])
def apoyar(usuario_id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT id,nombre,username,link_apoyo FROM usuarios WHERE id=%s',(usuario_id,)); creador=cur.fetchone(); cur.close(); c.close()
    if not creador: return 'Creador no encontrado',404
    if request.method=='POST':
        monto=float(request.form.get('monto','0') or 0)
        if monto<=0: flash('Monto inválido.','error'); return render_template('apoyar.html',creador=creador)
        token=os.getenv('MERCADOPAGO_ACCESS_TOKEN','').strip()
        if token:
            import requests
            base=os.getenv('VIBRA_BASE_URL','http://127.0.0.1:5000').rstrip('/')
            payload={'items':[{'title':f'Apoyo a {creador["nombre"]}','quantity':1,'currency_id':'CLP','unit_price':monto}], 'back_urls':{'success':base+'/apoyo/resultado','failure':base+'/apoyo/resultado','pending':base+'/apoyo/resultado'},'external_reference':f'{session["usuario_id"]}:{usuario_id}:{monto}'}
            r=requests.post('https://api.mercadopago.com/checkout/preferences',json=payload,headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'},timeout=15)
            if r.ok:
                data=r.json(); c=db(); cur=c.cursor(); cur.execute('INSERT INTO apoyos(donante_id,creador_id,monto,moneda,estado,proveedor,referencia) VALUES(%s,%s,%s,%s,%s,%s,%s)',(session['usuario_id'],usuario_id,monto,'CLP','pendiente','mercadopago',data.get('id'))); c.commit(); cur.close(); c.close(); return redirect(data.get('init_point') or data.get('sandbox_init_point'))
        if creador.get('link_apoyo'): return redirect(creador['link_apoyo'])
        flash('El creador todavía no ha configurado un método de apoyo.','error')
    return render_template('apoyar.html',creador=creador)

@app.route('/apoyo/resultado')
def apoyo_resultado(): return render_template('apoyo_resultado.html')

@app.route('/mensajes')
def mensajes():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT u.id,u.nombre,u.username,u.foto_perfil,MAX(m.fecha) ultima FROM usuarios u JOIN mensajes m ON (m.remitente_id=u.id AND m.destinatario_id=%s) OR (m.destinatario_id=u.id AND m.remitente_id=%s) WHERE u.id<>%s GROUP BY u.id ORDER BY ultima DESC',(session['usuario_id'],session['usuario_id'],session['usuario_id'])); chats=cur.fetchall(); cur.close(); c.close(); return render_template('mensajes.html',chats=chats)

@app.route('/mensajes/<int:usuario_id>',methods=['GET','POST'])
def chat(usuario_id):
    if 'usuario_id' not in session: return redirect(url_for('login'))
    c=db(); cur=c.cursor(dictionary=True); cur.execute('SELECT id,nombre,username,foto_perfil FROM usuarios WHERE id=%s',(usuario_id,)); otro=cur.fetchone()
    if not otro: cur.close(); c.close(); return 'Usuario no encontrado',404
    if request.method=='POST':
        texto=request.form.get('mensaje','').strip()
        if texto: cur.execute('INSERT INTO mensajes(remitente_id,destinatario_id,mensaje) VALUES(%s,%s,%s)',(session['usuario_id'],usuario_id,texto)); c.commit()
    cur.execute('UPDATE mensajes SET leido=1 WHERE remitente_id=%s AND destinatario_id=%s',(usuario_id,session['usuario_id'])); c.commit(); cur.execute('SELECT m.*,u.nombre,u.username FROM mensajes m JOIN usuarios u ON u.id=m.remitente_id WHERE (m.remitente_id=%s AND m.destinatario_id=%s) OR (m.remitente_id=%s AND m.destinatario_id=%s) ORDER BY m.fecha',(session['usuario_id'],usuario_id,usuario_id,session['usuario_id'])); msgs=cur.fetchall(); cur.close(); c.close(); return render_template('chat.html',otro=otro,mensajes=msgs)

@app.route('/configuracion',methods=['GET','POST'])
def configuracion():
    if 'usuario_id' not in session: return redirect(url_for('login'))
    if request.method=='POST':
        email=request.form.get('email','').strip().lower(); c=db(); cur=c.cursor(); cur.execute('UPDATE usuarios SET email=%s WHERE id=%s',(email,session['usuario_id'])); c.commit(); cur.close(); c.close(); flash('Configuración guardada.','ok')
    return render_template('configuracion.html',usuario=current_user())

@app.route('/api/publicacion/<int:publicacion_id>/eliminar',methods=['POST'])
def eliminar_publicacion(publicacion_id):
    if 'usuario_id' not in session:
        return jsonify(error='login'),401

    c=db()
    cur=c.cursor(dictionary=True)
    cur.execute('SELECT imagen,video FROM publicaciones WHERE id=%s AND usuario_id=%s',(publicacion_id,session['usuario_id']))
    publicacion=cur.fetchone()

    if not publicacion:
        cur.close(); c.close()
        return jsonify(ok=False,error='No tienes permiso para eliminar esta publicación.'),403

    cur.execute('DELETE FROM publicaciones WHERE id=%s AND usuario_id=%s',(publicacion_id,session['usuario_id']))
    c.commit()
    ok=cur.rowcount>0
    cur.close(); c.close()

    if ok:
        for filename in (publicacion.get('imagen'),publicacion.get('video')):
            if filename:
                if filename.startswith(('videos/', 'images/')):
                    try:
                        s3.delete_object(
                            Bucket=S3_BUCKET_NAME,
                            Key=filename
                            )
                    except Exception as e:
                        print('Error eliminando archivo del Bucket:', e)
    else:
        path=os.path.join(app.config['UPLOAD_FOLDER'],filename)
        try:
            if os.path.isfile(path): os.remove(path)
        except OSError:
            pass

    return jsonify(ok=ok)

@app.route('/uploads/<path:filename>')
def uploads(filename):
    carpetas_bucket = ('videos/', 'profiles/', 'covers/', 'images/', 'stories/')

    if filename.startswith(carpetas_bucket):
        try:
            url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET_NAME,
                    'Key': filename
                },
                ExpiresIn=3600
            )
            return redirect(url)
        except Exception as e:
            print('Error generando URL desde el Bucket:', e)
            return 'Archivo no disponible', 404

    return send_from_directory(UPLOAD_FOLDER, filename)
@app.route('/music/<path:filename>')
def music_file(filename): return send_from_directory(MUSIC_FOLDER,filename)
@app.route('/manifest.json')
def manifest(): return send_from_directory(os.path.join(BASE,'static'),'manifest.json')
@app.route('/service-worker.js')
def service_worker(): return send_from_directory(os.path.join(BASE,'static'),'service-worker.js')

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
