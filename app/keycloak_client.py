from keycloak import KeycloakAdmin
from .config import settings
import logging

logger = logging.getLogger(__name__)

class KeycloakClient:
    def __init__(self):
        self.kc_admin = KeycloakAdmin(server_url=settings.KEYCLOAK_SERVER_URL,
                                      username=None, password=None,
                                      realm_name=settings.KEYCLOAK_REALM,
                                      client_id=settings.KEYCLOAK_CLIENT_ID,
                                      client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
                                      verify=True)
    def get_user_id_by_username_or_email(self, username_or_email):
        # Returns first matched user id
        users = self.kc_admin.get_users({"username": username_or_email}) or []
        if not users:
            users = self.kc_admin.get_users({"email": username_or_email}) or []
        if not users:
            return None
        return users[0]["id"]

    def assign_realm_role(self, user_id, role_name):
        role = self.kc_admin.get_realm_role(role_name)
        if not role:
            raise Exception("role not found")
        self.kc_admin.assign_realm_role(user_id=user_id, roles=[role])
        logger.info("Assigned role %s to user %s", role_name, user_id)
