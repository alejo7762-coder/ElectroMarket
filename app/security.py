import os
import jwt

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

if not SECRET_KEY:
    raise RuntimeError("No se configuró JWT_SECRET_KEY en .env")

bearer_scheme = HTTPBearer()


def crear_token_acceso(usuario):
    ahora = datetime.now(timezone.utc)

    payload = {
        "sub": str(usuario["id_usuario"]),
        "correo": usuario["correo"],
        "iat": ahora,
        "exp": ahora + timedelta(minutes=EXPIRE_MINUTES)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def obtener_usuario_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        id_usuario = payload.get("sub")

        if not id_usuario:
            raise ValueError("Token sin identificador de usuario")

        return int(id_usuario)

    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado.",
            headers={"WWW-Authenticate": "Bearer"}
        )