# Implements: WC027-01b — WC027-01ba
# constitutional_basis: C-059, C-082
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from markup.router import router as markup_router

app = FastAPI(title="Billing Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(markup_router, prefix="/markup", tags=["markup"])

@app.get("/health")
def health_check() -> dict:
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)