# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.v1.auth import router as auth_router
from api.v1.kb_upload import router as kb_upload_router
from api.v1.kb import router as kb_router
from api.v1.admin import router as admin_router
from api.v1.llm import router as llm_router
from api.v1.plans import router as plans_router
from api.v1.crm_cfg import router as crm_cfg_router
#from api.v1.tenants import router as tenants_router
from api.v1.tenants_profile import router as tenants_router
from api.v1.admin_tenant_logo import router as admin_tenant_logo_router 
from api.v1.tenants_members import router as tenants_members_router

app = FastAPI(title="Annie API", version="1.2")


origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

#app.add_middleware(
#    CORSMiddleware,
#    allow_origins=origins or ["*"],
#    allow_origin_regex=".*",
#    allow_credentials=True,
#    allow_methods=["*"],
#    allow_headers=["*"],
#)



@app.get("/health")
def health(): return {"ok": True}

app.include_router(auth_router)
app.include_router(kb_upload_router)
app.include_router(kb_router)
app.include_router(admin_router)
app.include_router(llm_router)
app.include_router(plans_router)
app.include_router(crm_cfg_router)
app.include_router(tenants_router)
app.include_router(admin_tenant_logo_router)
app.include_router(tenants_members_router)
