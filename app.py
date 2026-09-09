"""
CUU Studio — servicio web de renderizado de piezas.

Expone la plantilla de frase diaria (cuu_daily_quote.py) como una API HTTP
para que n8n (u otro flujo) le mande una foto + una frase y reciba de vuelta
el PNG final ya compuesto — reemplaza por completo al nodo `editImage` de n8n.

Endpoints:
  GET  /health              -> {"ok": true}
  POST /render/daily-quote  -> recibe multipart/form-data:
                                  - image: archivo de imagen (foto real)
                                  - lines: JSON string, ej:
                                    '[{"text":"...", "color":"white"}, ...]'
                                  - object_position (opcional, default "50% 20%")
                                  - font_size (opcional, default 50)
                               Responde con el PNG (image/png).

Ejecutar localmente:
    pip install fastapi uvicorn python-multipart playwright
    playwright install chromium --with-deps
    uvicorn app:app --host 0.0.0.0 --port 8000
"""

import asyncio
import functools
import json
import os
import tempfile
import uuid

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from cuu_daily_quote import render_daily_quote

app = FastAPI(title="CUU Studio Render Service")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/render/daily-quote")
async def render_daily_quote_endpoint(
    image: UploadFile = File(...),
    lines: str = Form(...),
    object_position: str = Form("50% 20%"),
    font_size: int = Form(50),
):
    try:
        parsed_lines = json.loads(lines)
        if not isinstance(parsed_lines, list) or not parsed_lines:
            raise ValueError("`lines` debe ser una lista JSON no vacía de {text, color}.")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"`lines` inválido: {e}")

    work_id = uuid.uuid4().hex
    tmp_dir = tempfile.mkdtemp(prefix=f"cuu_{work_id}_")
    image_path = os.path.join(tmp_dir, f"input_{image.filename or 'photo.jpg'}")
    html_path = os.path.join(tmp_dir, "post.html")
    png_path = os.path.join(tmp_dir, "post.png")

    with open(image_path, "wb") as f:
        f.write(await image.read())

    try:
        # render_daily_quote usa la API SÍNCRONA de Playwright, que no puede
        # correr dentro del event loop de FastAPI/uvicorn (asyncio). Se ejecuta
        # en un hilo aparte para evitar el error "Sync API inside asyncio loop".
        render_fn = functools.partial(
            render_daily_quote,
            image_path=image_path,
            lines=parsed_lines,
            out_html=html_path,
            out_png=png_path,
            object_position=object_position,
            font_size=font_size,
        )
        await asyncio.to_thread(render_fn)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al renderizar: {e}")

    if not os.path.exists(png_path):
        raise HTTPException(status_code=500, detail="El render no generó el PNG esperado.")

    # El contenido real ahora es JPEG (ver cuu_daily_quote.py._rasterize) para
    # reducir el tamaño de la respuesta y evitar que la conexión se corte a
    # mitad de la descarga en redes con problemas para transferencias largas.
    return FileResponse(png_path, media_type="image/jpeg", filename="cuu_studio_frase.jpg")
