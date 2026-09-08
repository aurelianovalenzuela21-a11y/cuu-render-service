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
    image_b64 = _b64_image(image_path)
    html = _render_html(image_b64, lines, object_position, font_size)
    with open(out_html, "w") as f:
        f.write(html)
    if out_png:
        _rasterize(out_html, out_png, 1080, 1920, max_block_height=max_block_height, min_font_size=min_font_size)
    return out_html


def _rasterize(html_path, png_path, width, height, scale=2, max_block_height=None, min_font_size=30):
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
        page.wait_for_timeout(350)

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
