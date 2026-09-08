"""
CUU Studio — plantilla simplificada para FRASES DIARIAS (post 9:16).

Variante reducida de la plantilla completa (cuu_studio_template.py), pensada
para publicar una frase por día:
  - Foto real de fondo (mismo sistema de fondo con degradado + fundido a negro).
  - Solo DOS tonos de texto: blanco y degradado morado->rosa (#8FA6FF -> #E879F9).
  - Todas las líneas de la frase van al MISMO tamaño de fuente, centradas en un
    solo bloque de texto (sin kicker, sin body_copy, sin cursiva/acento distinto).
  - Sin íconos de servicios, sin teléfono.
  - Arriba: wordmark "CUU STUDIO". Abajo: "www.cuustudio.com". Ambos en blanco/degradado.

Uso:
    from cuu_daily_quote import render_daily_quote
    render_daily_quote(
        image_path="/ruta/a/foto.jpg",
        lines=[
            {"text": "DETRÁS DE CADA ÉXITO", "color": "white"},
            {"text": "hay horas que nadie vio", "color": "gradient"},
        ],
        out_html="post.html",
        out_png="post.png",
    )
"""

import base64
import os

FONT_LINK = ('<link href="https://fonts.googleapis.com/css2?'
             'family=Bricolage+Grotesque:opsz,wght@12..96,400..800&'
             'family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">')

CSS = """
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Bricolage Grotesque', sans-serif; }
.stage { position:relative; width:1080px; height:1920px; overflow:hidden; }
.bg { position:absolute; inset:0; background: radial-gradient(120% 90% at 15% 0%, #1B1440 0%, #0A0A16 55%, #050509 100%); }
.photo { position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }
.fade {
  position:absolute; inset:0;
  background: linear-gradient(to bottom,
    rgba(5,5,9,0.15) 0%,
    rgba(5,5,9,0.35) 38%,
    rgba(5,5,9,0.82) 62%,
    rgba(5,5,9,0.98) 80%,
    #050509 100%);
}
.brandmark {
  display:flex; align-items:center; justify-content:center; gap:11px;
  font-weight:800; letter-spacing:0.04em; font-size:24px; color:#fff;
}
.brandmark .dot { width:9px; height:9px; border-radius:50%; background:linear-gradient(135deg,#8FA6FF,#E879F9); }
.quote-box {
  position:absolute; left:150px; right:150px; top:50%; transform:translateY(-50%);
  display:flex; flex-direction:column; align-items:center; gap:24px;
}
.quote-text {
  width:100%; text-align:center;
  font-weight:800; font-size:50px; line-height:1.3; letter-spacing:0.005em;
  word-wrap:break-word; overflow-wrap:break-word;
}
.quote-text .white { color:#FFFFFF; }
.quote-text .gradient {
  background:linear-gradient(90deg,#8FA6FF,#E879F9);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
.site {
  position:absolute; bottom:70px; left:0; right:0; text-align:center;
  font-family:'Space Mono', monospace; font-weight:700; font-size:28px;
  letter-spacing:0.03em;
  background:linear-gradient(90deg,#8FA6FF,#E879F9);
  -webkit-background-clip:text; background-clip:text; color:transparent;
}
"""


def _b64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# Fracción de la altura del stage (1920px) donde queremos que caiga el CENTRO
# de la cara detectada. El bloque de texto va centrado en el stage (~top 50%,
# ocupando aproximadamente del 38% al 62% de alto según cuántas líneas tenga),
# así que colocamos la cara bien arriba de esa franja, con margen de sobra.
_FACE_TARGET_Y_FRAC = 0.24

_face_cascades = {}


def _get_cascade(name):
    if name not in _face_cascades:
        import cv2
        _face_cascades[name] = cv2.CascadeClassifier(cv2.data.haarcascades + name)
    return _face_cascades[name]


def _detect_heads(img):
    """
    Detecta TODAS las cabezas humanas visibles en la foto (no solo "la cara
    más grande"), combinando varios detectores en orden de confiabilidad:

    Cara de frente / perfil, con varias combinaciones de cascada +
    preprocesado (incluyendo ecualización de histograma para el contraste
    bajo típico de luz de ambiente morada/azul en estudio de grabación), en
    orden de confiabilidad — se usan TODAS las que encuentren algo.

    NOTA: se probó agregar un cascade de "cabeza+hombros" (upperbody) como
    respaldo para poses sin cara visible (cabeza agachada, gorra), pero ese
    cascade concreto resultó tener un bug de memoria nativo en esta versión
    de OpenCV — corrompe memoria y tumba el proceso completo con
    "free(): invalid next size" / Segmentation fault, algo que NINGÚN
    try/except en Python puede atrapar (no es una excepción, es un crash a
    nivel de proceso). Se quitó por completo; mejor no detectar una cabeza
    difícil que tumbar el servicio para TODAS las peticiones en curso.

    Devuelve una lista de cajas (x, y, w, h) — puede tener 0, 1 o varias
    cabezas. Si hay varias, el llamador debe centrar el recorte en el punto
    medio del grupo completo, no en una sola cabeza.
    """
    import cv2

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)
    img_w = img.shape[1]
    min_size = max(40, int(img_w * 0.035))

    face_attempts = [
        ("haarcascade_frontalface_alt2.xml", gray_eq, 1.05, 4),
        ("haarcascade_frontalface_default.xml", gray_eq, 1.05, 4),
        ("haarcascade_frontalface_alt2.xml", gray, 1.1, 4),
        ("haarcascade_frontalface_default.xml", gray, 1.1, 5),
        ("haarcascade_profileface.xml", gray_eq, 1.05, 4),
        ("haarcascade_profileface.xml", gray, 1.1, 4),
    ]
    found = []
    for cascade_name, gray_img, scale_factor, min_neighbors in face_attempts:
        try:
            faces = _get_cascade(cascade_name).detectMultiScale(
                gray_img, scaleFactor=scale_factor, minNeighbors=min_neighbors,
                minSize=(min_size, min_size),
            )
        except cv2.error:
            # Algunas combinaciones de cascada/escala pueden disparar un bug
            # interno de OpenCV con ciertas imágenes (assertion en
            # cascadedetect.hpp) — se descarta ese intento y se sigue con
            # el siguiente en vez de tronar toda la petición.
            continue
        found.extend(tuple(f) for f in faces)

    return found


def _group_center(boxes):
    """
    Punto medio del grupo completo de cabezas detectadas: la caja envolvente
    (bounding box) que cubre TODAS las cabezas, y el centro de esa caja. Con
    una sola cabeza esto es simplemente su centro; con varias, es el centro
    del grupo — tal como se pidió: centrar cualquier cabeza, y si hay varias,
    el centro del grupo.
    """
    xs1 = [b[0] for b in boxes]
    ys1 = [b[1] for b in boxes]
    xs2 = [b[0] + b[2] for b in boxes]
    ys2 = [b[1] + b[3] for b in boxes]
    x1, y1, x2, y2 = min(xs1), min(ys1), max(xs2), max(ys2)
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    return cx, cy


def _reposition_face_above_text(image_path, target_w=1080, target_h=1920,
                                 target_y_frac=_FACE_TARGET_Y_FRAC):
    """
    Detecta la cara más grande en la foto y recorta/encuadra la imagen a la
    proporción del stage (1080x1920) de forma que la cara quede SIEMPRE por
    encima de donde va el texto, en vez de depender de un object-position
    fijo que no se ajusta a cada foto.

    Devuelve (b64_png, True) si se detectó y recortó una cara, o (None, False)
    si no se detectó ninguna (en ese caso el llamador debe usar el
    comportamiento anterior con object_position).
    """
    import cv2
    import numpy as np
    from PIL import Image

    img = cv2.imread(image_path)
    if img is None:
        return None, False

    try:
        heads = _detect_heads(img)
    except Exception:
        # Cualquier falla inesperada en la detección no debe tronar el
        # render completo — se cae al encuadre por default.
        heads = []
    if not heads:
        return None, False

    face_cx, face_cy = _group_center(heads)

    img_h, img_w = img.shape[:2]
    target_aspect = target_w / target_h  # 0.5625

    # Zoom mínimo para garantizar que, aunque la cara esté muy centrada en la
    # foto original, siempre haya suficiente "colchón" vertical para
    # desplazarla hacia arriba sin dejar bordes vacíos.
    min_extra_zoom = 1.25

    img_aspect = img_w / img_h
    if img_aspect > target_aspect:
        # La foto es más ancha que el stage -> se recorta por los lados,
        # el alto completo ya cabe. Aplicamos el zoom extra igual para tener
        # margen vertical de sobra.
        crop_h = img_h / min_extra_zoom
        crop_w = crop_h * target_aspect
    else:
        # La foto es más "alta" que el stage (o igual) -> normalmente se
        # recorta por arriba/abajo. Damos zoom extra para tener margen.
        crop_w = img_w / min_extra_zoom
        crop_h = crop_w / target_aspect

    crop_w = min(crop_w, img_w)
    crop_h = min(crop_h, img_h)

    # Posición vertical del recorte: queremos que la cara caiga en
    # target_y_frac de la ALTURA DEL RECORTE (no de la foto completa).
    desired_top = face_cy - target_y_frac * crop_h
    top = max(0, min(desired_top, img_h - crop_h))

    # Horizontal: centrado en la cara, sin salirse de los bordes.
    desired_left = face_cx - crop_w / 2.0
    left = max(0, min(desired_left, img_w - crop_w))

    box = (int(left), int(top), int(left + crop_w), int(top + crop_h))
    pil_img = Image.open(image_path).convert("RGB")
    cropped = pil_img.crop(box).resize((target_w, target_h), Image.LANCZOS)

    import io
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode(), True


def _render_html(image_b64, lines, object_position, font_size=50):
    # Un solo bloque de texto que fluye y se envuelve de forma natural (nunca se
    # sale de la caja), con spans inline por color en vez de lineas fijas.
    spans = " ".join(
        f'<span class="{l.get("color","white")}">{l["text"]}</span>'
        for l in lines
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8">{FONT_LINK}<style>{CSS}</style></head>
<body>
  <div class="stage">
    <div class="bg"></div>
    <img class="photo" src="data:image/jpeg;base64,{image_b64}" style="object-position:{object_position};">
    <div class="fade"></div>
    <div class="quote-box">
      <div class="quote-text" id="quoteText" style="font-size:{font_size}px;">{spans}</div>
      <div class="brandmark"><span class="dot"></span>CUU STUDIO</div>
    </div>
    <div class="site">www.cuustudio.com</div>
  </div>
</body></html>"""


def render_daily_quote(image_path, lines, out_html, out_png=None, object_position="50% 20%",
                        font_size=50, max_block_height=620, min_font_size=30):
    """
    image_path: foto real de CUU Studio (vertical de preferencia).
    lines: lista de {"text": str, "color": "white"|"gradient"} — todas al mismo tamaño,
           centradas en un solo bloque que se envuelve solo (nunca se sale de la caja).
           Usa "gradient" para resaltar la parte clave de la frase.
    max_block_height: si el texto (ya envuelto) mide mas alto que esto en px, el tamano
           de fuente se reduce automaticamente hasta que quepa (o hasta min_font_size).
    """
    # Intenta recortar/encuadrar la foto según la cara detectada para que
    # siempre quede arriba del texto. Si no se detecta ninguna cara, se cae
    # de forma segura al comportamiento anterior (object_position fijo).
    face_b64, face_found = _reposition_face_above_text(image_path, target_w=1080, target_h=1920)
    if face_found:
        image_b64 = face_b64
        effective_object_position = "50% 50%"  # ya viene recortado exacto
    else:
        image_b64 = _b64_image(image_path)
        effective_object_position = object_position

    html = _render_html(image_b64, lines, effective_object_position, font_size)
    with open(out_html, "w") as f:
        f.write(html)
    if out_png:
        _rasterize(out_html, out_png, 1080, 1920, max_block_height=max_block_height, min_font_size=min_font_size)
    return out_html


def _rasterize(html_path, png_path, width, height, scale=1, max_block_height=None, min_font_size=30):
    from playwright.sync_api import sync_playwright
    # En el sandbox de desarrollo Chromium vive en /opt/pw-browsers/chromium;
    # en el contenedor Docker del servicio (imagen oficial de Playwright) usa
    # la ruta por defecto del propio Playwright. Se prueba la ruta local y si
    # no existe se deja que Playwright resuelva la suya.
    _local_chromium = "/opt/pw-browsers/chromium"
    launch_kwargs = {"executable_path": _local_chromium} if os.path.exists(_local_chromium) else {}
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
        page.goto("file://" + os.path.abspath(html_path))
        # Espera a que las webfonts (Bricolage Grotesque / Space Mono) terminen
        # de cargar antes de medir o capturar nada — si no, Chromium puede
        # pintar primero con la fuente de respaldo y luego con la webfont ya
        # cargada casi en el mismo frame, dejando un "fantasma" de texto
        # duplicado en la captura (dos tamaños/pesos de letra superpuestos).
        try:
            page.wait_for_function("document.fonts.status === 'loaded'", timeout=4000)
        except Exception:
            pass
        # document.fonts.ready puede resolver un frame antes de que Chromium
        # termine de repintar con la webfont ya aplicada — forzamos dos
        # vueltas de animation-frame para asegurar que el repintado real ya
        # ocurrió antes de medir/capturar (si no, la captura puede mezclar
        # el layout con fuente de respaldo y el layout con la webfont).
        page.evaluate(
            "async () => { await document.fonts.ready; "
            "await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }"
        )
        page.wait_for_timeout(300)

        if max_block_height:
            # Reduce el tamano de fuente hasta que el bloque de texto quepa dentro
            # de max_block_height, para que la frase NUNCA se salga de su caja.
            for size in range(200):
                box = page.eval_on_selector("#quoteText", "el => el.getBoundingClientRect()")
                current_size = page.eval_on_selector(
                    "#quoteText", "el => parseFloat(getComputedStyle(el).fontSize)"
                )
                if box["height"] <= max_block_height or current_size <= min_font_size:
                    break
                new_size = max(min_font_size, current_size - 2)
                page.eval_on_selector(
                    "#quoteText", "(el, s) => el.style.fontSize = s + 'px'", new_size
                )
            page.wait_for_timeout(80)

        page.screenshot(path=png_path)
        browser.close()


if __name__ == "__main__":
    print(__doc__)
