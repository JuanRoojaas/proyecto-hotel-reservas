"""Detalle técnico: cómo se cifran las contraseñas (RNF-03)."""
import bcrypt

COSTO = 10


class BcryptHasher:

    def generar(self, password):
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(COSTO)).decode("utf-8")

    def verificar(self, password, hash_guardado):
        return bcrypt.checkpw(password.encode("utf-8"), hash_guardado.encode("utf-8"))
