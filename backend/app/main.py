from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import audit_simulation, auth, clauses, documents, findings, onboarding, organization, reports, vendor_audit, vendors

app = FastAPI(title="DeviationTrace API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(findings.router)
app.include_router(clauses.router)
app.include_router(reports.router)
app.include_router(audit_simulation.router)
app.include_router(vendor_audit.router)
app.include_router(onboarding.router)
app.include_router(vendors.router)
app.include_router(organization.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
