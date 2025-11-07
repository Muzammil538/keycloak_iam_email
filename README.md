# keycloak_iam_email
```
keycloak-email-iam/
├─ .env.example
├─ requirements.txt
├─ alembic/                     # optional alembic migrations (skeleton)
├─ alembic.ini
├─ app/
│  ├─ __init__.py
│  ├─ main.py                   # FastAPI app (entrypoint)
│  ├─ config.py                 # config from env
│  ├─ db.py                     # SQLAlchemy engine/session, create_tables()
│  ├─ models.py                 # SQLAlchemy models
│  ├─ schemas.py                # Pydantic request/response models
│  ├─ keycloak_client.py        # Keycloak helper wrapper
│  ├─ mailer.py                 # Smpt email helpers
│  ├─ tokens.py                 # token create/validate + DB token table helpers
│  ├─ tasks.py                  # APScheduler tasks (send email & reminders)
│  ├─ templates/
│  │   ├─ approve_email.html
│  │   └─ approve_email.txt
│  └─ utils.py                  # helpers (links, logging helpers)
├─ run_windows_service.bat      # sample wrapper to run app with uvicorn
├─ run_dev.bat                  # run dev server
├─ README.md
└─ tests/
   ├─ test_token.py
   └─ test_mailer.py
```