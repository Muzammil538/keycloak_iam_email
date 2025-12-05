from importlib import import_module
from .config import settings

def get_mailer():
    backend = settings.MAILER_BACKEND
    if backend == "mailersend":
        mod = import_module("app.mailers.mailersend_adapter")
    else:
        mod = import_module("app.mailer_smtp")
    return mod.send_email

