-- =====================================================================
-- Hotel Cancun Resort & Spa - Corte vertical "Reservar una habitación"
-- Recrea la base desde cero: ejecutar antes de 02_seed.sql
-- =====================================================================

DROP DATABASE IF EXISTS hotel_corte_vertical;
CREATE DATABASE hotel_corte_vertical CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hotel_corte_vertical;

-- RF-01: usuarios. Los ALTER del modelo original se integraron en un solo CREATE.
-- `password` guarda el hash bcrypt, nunca la contraseña en texto plano (RNF-03).
CREATE TABLE usuarios (
    id_usuario        INT AUTO_INCREMENT PRIMARY KEY,
    nombre            VARCHAR(100) NOT NULL,
    apellido          VARCHAR(100) NOT NULL,
    fecha_nacimiento  DATE         NULL,
    correo            VARCHAR(100) NOT NULL,
    password          VARCHAR(255) NOT NULL,
    rol               ENUM('huesped', 'recepcionista', 'administrador') NOT NULL DEFAULT 'huesped',
    codigo_2fa        VARCHAR(6)   NULL,
    verificado        BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_usuarios_correo UNIQUE (correo)
);

-- RF-02 y RF-03: habitaciones físicas.
-- `estado` es el estado operativo ('disponible' o 'mantenimiento'), NO la ocupación:
-- si una habitación está libre o no depende de las fechas y se calcula con reservas_noches.
CREATE TABLE habitaciones (
    id_habitacion  INT AUTO_INCREMENT PRIMARY KEY,
    numero         VARCHAR(10)   NOT NULL,
    tipo           VARCHAR(50)   NOT NULL,
    precio         DECIMAL(10,2) NOT NULL,
    estado         VARCHAR(20)   NOT NULL DEFAULT 'disponible',
    descripcion    TEXT          NULL,
    CONSTRAINT uq_habitaciones_numero UNIQUE (numero),
    CONSTRAINT ck_habitaciones_precio CHECK (precio > 0),
    CONSTRAINT ck_habitaciones_estado CHECK (estado IN ('disponible', 'mantenimiento'))
);

-- RF-03: reservas de los huéspedes.
CREATE TABLE reservas (
    id_reserva     INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario     INT         NOT NULL,
    id_habitacion  INT         NOT NULL,
    fecha_inicio   DATE        NOT NULL,
    fecha_fin      DATE        NOT NULL,
    estado         VARCHAR(20) NOT NULL DEFAULT 'confirmada',
    CONSTRAINT fk_reservas_usuario    FOREIGN KEY (id_usuario)    REFERENCES usuarios(id_usuario),
    CONSTRAINT fk_reservas_habitacion FOREIGN KEY (id_habitacion) REFERENCES habitaciones(id_habitacion),
    CONSTRAINT ck_reservas_fechas CHECK (fecha_fin > fecha_inicio)
);

-- NUEVA (RF-02 y RF-03): una fila por cada noche ocupada.
-- UNIQUE (id_habitacion, fecha) impide que dos reservas ocupen la misma
-- habitación la misma noche, incluso con solicitudes simultáneas.
CREATE TABLE reservas_noches (
    id_reserva     INT  NOT NULL,
    id_habitacion  INT  NOT NULL,
    fecha          DATE NOT NULL,
    PRIMARY KEY (id_reserva, fecha),
    CONSTRAINT uq_noches_habitacion_fecha UNIQUE (id_habitacion, fecha),
    CONSTRAINT fk_noches_reserva    FOREIGN KEY (id_reserva)    REFERENCES reservas(id_reserva) ON DELETE CASCADE,
    CONSTRAINT fk_noches_habitacion FOREIGN KEY (id_habitacion) REFERENCES habitaciones(id_habitacion)
);
