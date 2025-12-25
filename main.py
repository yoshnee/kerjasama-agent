from fastapi import FastAPI

app = FastAPI(title="Kerjasama Agent", version="0.1.0")


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
