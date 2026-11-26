from fastapi import FastAPI

from app.routers import auth, categories, imports, reports, transactions

app = FastAPI(title="Expense Tracker")

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(reports.router)
app.include_router(imports.router)


@app.get("/")
def health():
    return {"status": "ok"}