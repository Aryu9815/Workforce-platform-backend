# Workforce-platform-backend

## Setup Instructions

1. Create two database tenants: "common" and client's tenant.
2. Run `tenant_schemas.sql` in tenant DB and `common_schemas.sql` in common DB, then execute `tenant_insert.sql` and `common_insert.sql` in respective schemas.
3. Create virtual environment: `python -m venv venv`
4. Install dependencies: `pip install -r requirements.txt`
5. Configure environment file using `sample_env.txt`.
6. Install and start Redis via Docker:
   - Pull Redis image: `docker pull redis`
   - Run Redis: `docker run -d -p 6379:6379 redis`
7. Set email app password in environment file for notifications.
8. Create user in DB via query, manually assign permissions and roles.
9. Start server: `uvicorn app.main:app --reload`

