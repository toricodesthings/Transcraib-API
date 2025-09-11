from fastapi import APIRouter
from fastapi.responses import JSONResponse, HTMLResponse
import os

router = APIRouter()

# Root endpoint serving a simple HTML inteface for testing & debugging
@router.get("/")
async def read_root():
    try:
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_interface.html")
        with open(html_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": "Error loading test interface", "error": str(e)},
        )
    