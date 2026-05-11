from dataclasses import dataclass
from typing import Optional

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@dataclass(frozen=True)
class TenantContext:
    id: int
    slug: str = ""
    nombre: str = ""


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request):
        self._attach_tenant(request)
        return self.get_response(request)

    def _attach_tenant(self, request) -> None:
        tenant = None
        header = self.jwt_auth.get_header(request)
        if header:
            raw_token = self.jwt_auth.get_raw_token(header)
            if raw_token:
                try:
                    validated = self.jwt_auth.get_validated_token(raw_token)
                    tenant = self._from_token(validated)
                except (InvalidToken, TokenError):
                    tenant = None

        if tenant is None:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                tenant = self._from_user(user)

        request.tenant = tenant

    def _from_user(self, user) -> Optional[TenantContext]:
        vet_id = getattr(user, "veterinaria_id", None)
        if not vet_id:
            return None

        veterinaria = getattr(user, "veterinaria", None)
        return TenantContext(
            id=vet_id,
            slug=getattr(veterinaria, "slug", "") or "",
            nombre=getattr(veterinaria, "nombre", "") or "",
        )

    def _from_token(self, token) -> Optional[TenantContext]:
        vet_id = token.get("id_veterinaria")
        if not vet_id:
            return None

        return TenantContext(
            id=vet_id,
            slug=token.get("veterinaria_slug", "") or "",
            nombre=token.get("veterinaria_nombre", "") or "",
        )
