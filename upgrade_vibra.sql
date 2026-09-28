USE vibra;

-- Ejecutar una sola vez sobre tu base actual.
-- Las tablas existentes se conservan.

ALTER TABLE usuarios
    ADD COLUMN foto_portada VARCHAR(255) NULL,
    ADD COLUMN link_apoyo VARCHAR(500) NULL,
    ADD COLUMN username VARCHAR(50) NULL UNIQUE;

ALTER TABLE publicaciones
    MODIFY imagen VARCHAR(255) NULL,
    ADD COLUMN tipo ENUM('imagen','video') NOT NULL DEFAULT 'imagen',
    ADD COLUMN video VARCHAR(255) NULL,
    ADD COLUMN musica_id INT NULL,
    ADD COLUMN ubicacion VARCHAR(150) NULL,
    ADD COLUMN hashtags VARCHAR(500) NULL;

CREATE TABLE IF NOT EXISTS canciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(120) NOT NULL,
    artista VARCHAR(120) NOT NULL,
    archivo VARCHAR(255) NOT NULL,
    portada VARCHAR(255) NULL,
    duracion INT NULL,
    usuario_id INT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS historias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    archivo VARCHAR(255) NOT NULL,
    tipo ENUM('imagen','video') NOT NULL DEFAULT 'imagen',
    texto VARCHAR(255) NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    expira DATETIME NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS historia_vistas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    historia_id INT NOT NULL,
    usuario_id INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(historia_id, usuario_id),
    FOREIGN KEY (historia_id) REFERENCES historias(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS guardados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    publicacion_id INT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usuario_id, publicacion_id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    actor_id INT NULL,
    tipo VARCHAR(40) NOT NULL,
    publicacion_id INT NULL,
    texto VARCHAR(255) NOT NULL,
    leida TINYINT(1) NOT NULL DEFAULT 0,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mensajes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    remitente_id INT NOT NULL,
    destinatario_id INT NOT NULL,
    mensaje VARCHAR(1000) NOT NULL,
    leido TINYINT(1) NOT NULL DEFAULT 0,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (remitente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (destinatario_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS apoyos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    donante_id INT NOT NULL,
    creador_id INT NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    moneda VARCHAR(5) NOT NULL DEFAULT 'CLP',
    estado VARCHAR(30) NOT NULL DEFAULT 'pendiente',
    proveedor VARCHAR(50) NULL,
    referencia VARCHAR(150) NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donante_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (creador_id) REFERENCES usuarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reportes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    publicacion_id INT NULL,
    usuario_reportado_id INT NULL,
    motivo VARCHAR(100) NOT NULL,
    detalle VARCHAR(500) NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (publicacion_id) REFERENCES publicaciones(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_reportado_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Si ya tienes usuarios antiguos, este paso puede ejecutarse después de la ALTER anterior.
UPDATE usuarios SET username = CONCAT('vibra_',id) WHERE username IS NULL OR username='';
