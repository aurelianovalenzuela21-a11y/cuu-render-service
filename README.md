# CUU Studio — Servicio de Renderizado

Reemplaza el nodo `editImage` de n8n. Recibe una foto + una frase por HTTP y
regresa el PNG final ya compuesto (9:16, texto blanco, autoajuste de tamaño,
wordmark CUU STUDIO y www.cuustudio.com), usando la plantilla aprobada
(HTML/CSS renderizado con Chromium vía Playwright).

## Desplegar en Railway (recomendado, más simple)

1. Crea un repo nuevo en GitHub y sube estos 5 archivos
   (`app.py`, `cuu_daily_quote.py`, `requirements.txt`, `Dockerfile`, este README).
2. En Railway: **New Project → Deploy from GitHub repo** → selecciona el repo.
3. Railway detecta el `Dockerfile` automáticamente y lo construye (puede tardar
   3-5 min la primera vez porque la imagen de Playwright pesa ~1.5GB).
4. En **Settings → Networking**, genera un dominio público (Railway te da algo
   como `https://cuu-render-service-production.up.railway.app`).
5. Prueba que esté vivo: abre `https://tu-dominio/health` — debe responder
   `{"ok": true}`.

## Desplegar en Render (alternativa)

1. Sube el mismo repo a GitHub.
2. En Render: **New → Web Service** → conecta el repo → Render detecta el
   Dockerfile solo. Elige el plan (el free tier se "duerme" tras inactividad,
   lo cual añade ~30-50s a la primera llamada tras un rato sin uso — si eso
   te molesta, usa el plan Starter de pago).
3. Copia la URL pública que te da Render al terminar el deploy.

## Probar el endpoint

```bash
curl -X POST https://TU-DOMINIO/render/daily-quote \
  -F "image=@/ruta/a/foto.jpg" \
  -F 'lines=[{"text":"DETRÁS DE CADA ÉXITO HAY","color":"white"},{"text":"HORAS DE ESTUDIO Y ARREGLOS QUE NADIE VIO","color":"white"}]' \
  --output resultado.png
```

## Cómo lo consume n8n

Una vez desplegado, en el workflow "CUU Studio — Frases Automáticas":

1. Se elimina el nodo `Calcular Centrado de Texto` (código de posicionamiento
   manual) y el nodo `Componer Pieza 9:16` (`editImage`).
2. En su lugar va un nodo **HTTP Request**:
   - Method: `POST`
   - URL: `https://TU-DOMINIO/render/daily-quote`
   - Body: `multipart-form-data`
     - `image` → binario de la foto (`Descargar Foto` / `Unir Frase + Foto`)
     - `lines` → JSON armado con la frase de Gemini, ej. vía un Code node:
       `[{"text": $json.quote.toUpperCase(), "color": "white"}]`
     - `object_position` (opcional)
   - Response: guardar como binario (`data`), igual que hacía `editImage`.
3. El resto del flujo (subir a Telegram, armar URL pública, enviar a
   Metricool) sigue exactamente igual — solo cambia de dónde sale el PNG.

Dile a Claude "ya desplegué el servicio, la URL es ___" y se conecta el
workflow de n8n a partir de ahí.
