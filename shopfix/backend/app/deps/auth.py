from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.services import auth as auth_service


def current_user_id(authorization: str | None = Header(default=None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, auth_service.SECRET, algorithms=[auth_service.ALGORITHM])
        return int(payload["sub"])
    except (JWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
