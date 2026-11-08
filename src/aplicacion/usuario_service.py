"""Caso de uso RF-01: registrar usuario.

El repositorio y el hasher llegan por el constructor (inyección de dependencias,
semana 9): así el servicio se prueba con un repositorio simulado (RNF-04).
"""
from src.dominio import reglas_reserva as reglas


class UsuarioService:

    def __init__(self, usuario_repo, hasher):
        self.usuario_repo = usuario_repo
        self.hasher = hasher

    def registrar(self, datos):
        reglas.validar_datos_registro(datos)

        existente = self.usuario_repo.buscar_por_correo(datos["correo"])
        reglas.validar_correo_disponible(existente is not None)

        password_hash = self.hasher.generar(datos["password"])
        id_usuario = self.usuario_repo.guardar(
            datos["nombre"], datos["apellido"], datos.get("fecha_nacimiento") or None,
            datos["correo"], password_hash,
        )
        # La respuesta nunca incluye la contraseña ni el hash (RNF-03).
        return {"mensaje": "Usuario registrado", "id_usuario": id_usuario,
                "nombre": datos["nombre"], "apellido": datos["apellido"],
                "correo": datos["correo"], "rol": "huesped"}
