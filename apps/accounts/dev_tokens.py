import jwt
from django.conf import settings

DEV_TOKEN_ISSUER = "vivamente-back-dev"


def create_dev_token(uid, email, role):
    payload = {"uid": uid, "email": email, "role": role, "iss": DEV_TOKEN_ISSUER}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_dev_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("iss") != DEV_TOKEN_ISSUER:
        return None
    return payload
