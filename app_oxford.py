import streamlit as st
import streamlit.components.v1 as components
import requests
import re

st.set_page_config(page_title="Verificador Oxford Talca", page_icon="🚲", layout="centered")

# --- ESTILOS VISUALES PARA CELULAR (PRECIOS Y STOCK GRANDES) ---
st.markdown("""
<style>
.tarjeta-producto {
    border: 2px solid #e0e0e0;
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 18px;
    background-color: #ffffff;
    color: #111111;
    box-shadow: 0 4px 10px rgba(0,0,0,0.06);
}
.titulo-prod {
    font-size: 1.25rem;
    font-weight: 800;
    color: #1a1a1a;
    margin-bottom: 6px;
}
.caja-codigos {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 12px;
}
.badge-codigo {
    background: #f1f3f5;
    color: #212529;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 700;
    border: 1px solid #ced4da;
}
.caja-precios {
    background: #f8fff9;
    border: 2px solid #2b8a3e;
    border-radius: 10px;
    padding: 12px;
    text-align: center;
    margin-bottom: 12px;
}
.precio-oferta {
    font-size: 2.2rem;
    font-weight: 900;
    color: #2b8a3e;
    line-height: 1.1;
}
.precio-normal {
    font-size: 1.05rem;
    color: #868e96;
    text-decoration: line-through;
    margin-right: 8px;
}
.badge-descuento {
    background: #e03131;
    color: white;
    padding: 3px 8px;
    border-radius: 6px;
    font-weight: 800;
    font-size: 0.9rem;
}
.grid-stock {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 10px;
}
.caja-stock {
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    font-weight: 700;
}
.stock-ok { background: #ebfbee; border: 2px solid #40c057; color: #1b4332; }
.stock-poco { background: #fff9db; border: 2px solid #fab005; color: #5c3c00; }
.stock-no { background: #fff5f5; border: 2px solid #fa5252; color: #7f1d1d; }
.label-sucursal { font-size: 0.8rem; text-transform: uppercase; opacity: 0.85; display: block; }
.valor-stock { font-size: 1.15rem; font-weight: 900; display: block; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

st.title("🚲 Verificador Oxford — Sucursal Talca")

# --- 1. CARGA DEL CATÁLOGO COMPLETO EN MEMORIA (ONLINE + TIENDA) ---
@st.cache_data(ttl=1800, show_spinner=False)
def cargar_catalogo_oxford():
    catalogo = []
    headers = {"User-Agent": "Mozilla/5.0"}
    # Descargamos las páginas del catálogo general de Shopify para buscar por código de barras y SKU al instante
    for pagina in range(1, 9):
        try:
            url = f"https://oxfordstore.cl/products.json?limit=250&page={pagina}"
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code != 200:
                break
            prods = r.json().get("products", [])
            if not prods:
                break
            catalogo.extend(prods)
        except Exception:
            break
    return catalogo

with st.spinner("Sincronizando catálogo de Oxford Store..."):
    catalogo_memoria = cargar_catalogo_oxford()

# --- 2. ESCÁNER HD CON DETECTOR NATIVO, ZOOM Y LINTERNA ---
escaner_hd_html = """
<script src="https://unpkg.com/html5-qrcode"></script>
<div style="text-align: center; font-family: sans-serif;">
  <div id="reader" style="width: 100%; max-width: 450px; margin: auto; border-radius: 12px; overflow: hidden; border: 2px solid #333;"></div>
  
  <div id="controles-camara" style="margin-top: 8px; display: flex; justify-content: center; gap: 10px; align-items: center; flex-wrap: wrap;">
    <label style="font-size: 13px; font-weight: bold;">🔍 Zoom:
      <input id="zoom-slider" type="range" min="1" max="3" step="0.2" value="1.5" oninput="aplicarZoom(this.value)" style="vertical-align: middle; width: 110px;">
    </label>
    <button id="btn-flash" onclick="toggleFlash()" style="padding: 6px 12px; border-radius: 6px; border: 1px solid #555; background: #222; color: #fff; font-size: 13px; cursor: pointer;">
      🔦 Linterna
    </button>
    <button id="btn-reiniciar" onclick="iniciarCamara()" style="display:none; padding: 6px 14px; border: none; border-radius: 6px; background: #0066cc; color: white; font-weight: bold; font-size: 13px; cursor: pointer;">
      🔄 Escanear otro
    </button>
  </div>

  <div id="estado" style="margin-top: 8px; font-weight: bold; color: #00a650; font-size: 14px;">
    📷 Aléjate a ~15 cm del código y usa el Zoom para mayor nitidez
  </div>
</div>

<script>
  let html5QrCode;
  let flashEncendido = false;
  let ultimoCodigo = "";
  let contadorLecturas = 0;

  function enviarAStreamlit(codigo) {
    try {
      const parentDoc = window.parent.document;
      const input = parentDoc.querySelector('input[aria-label="Código de barras, SKU o nombre del producto:"]');
      if (input) {
        const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
        setter.call(input, codigo);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
        setTimeout(() => {
          input.dispatchEvent(new window.parent.KeyboardEvent('keydown', {
            key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true
          }));
          input.blur();
        }, 60);
      }
    } catch (e) {
      console.log("Error enviando código:", e);
    }
  }

  function obtenerTrackVideo() {
    const video = document.querySelector("#reader video");
    if (video && video.srcObject) {
      const tracks = video.srcObject.getVideoTracks();
      if (tracks.length > 0) return tracks[0];
    }
    return null;
  }

  function aplicarZoom(valor) {
    const track = obtenerTrackVideo();
    if (track) {
      track.applyConstraints({ advanced: [{ zoom: parseFloat(valor) }] }).catch(() => {});
    }
  }

  function toggleFlash() {
    const track = obtenerTrackVideo();
    if (track) {
      flashEncendido = !flashEncendido;
      track.applyConstraints({ advanced: [{ torch: flashEncendido }] }).catch(() => {
        document.getElementById("estado").innerText = "⚠️ Este teléfono no permite activar la linterna desde el navegador.";
      });
    }
  }

  function iniciarCamara() {
    ultimoCodigo = "";
    contadorLecturas = 0;
    document.getElementById("btn-reiniciar").style.display = "none";
    document.getElementById("estado").innerText = "📷 Apunta al código (mantén a 15 cm para enfocar bien)";
    
    const formatos = [
      Html5QrcodeSupportedFormats.EAN_13,
      Html5QrcodeSupportedFormats.EAN_8,
      Html5QrcodeSupportedFormats.CODE_128,
      Html5QrcodeSupportedFormats.CODE_39,
      Html5QrcodeSupportedFormats.UPC_A,
      Html5QrcodeSupportedFormats.UPC_E,
      Html5QrcodeSupportedFormats.ITF,
      Html5QrcodeSupportedFormats.QR_CODE
    ];

    html5QrCode = new Html5Qrcode("reader", {
      formatsToSupport: formatos,
      experimentalFeatures: { useBarCodeDetectorIfSupported: true }
    });

    const config = {
      fps: 15,
      qrbox: { width: 280, height: 110 },
      videoConstraints: {
        facingMode: { exact: "environment" },
        width: { ideal: 1920 },
        height: { ideal: 1080 },
        focusMode: "continuous"
      }
    };

    html5QrCode.start(
      { facingMode: "environment" },
      config,
      (decodedText) => {
        // Exigimos 2 lecturas iguales seguidas para evitar códigos falsos por desenfoque
        if (decodedText === ultimoCodigo) {
          contadorLecturas++;
        } else {
          ultimoCodigo = decodedText;
          contadorLecturas = 1;
        }

        if (contadorLecturas >= 2) {
          document.getElementById("estado").innerText = "✅ Código confirmado: " + decodedText;
          document.getElementById("btn-reiniciar").style.display = "inline-block";
          enviarAStreamlit(decodedText);
          html5QrCode.stop();
        }
      },
      (err) => {}
    ).then(() => {
      // Aplicamos un ligero zoom inicial (1.5x) para mejorar el enfoque de códigos pequeños
      setTimeout(() => aplicarZoom(1.5), 500);
    }).catch((err) => {
      document.getElementById("estado").innerText = "⚠️ Da permiso a la cámara trasera en tu navegador.";
    });
  }

  iniciarCamara();
</script>
"""

with st.expander("📷 Escáner de Cámara Trasera HD (Con Zoom y Linterna)", expanded=True):
    components.html(escaner_hd_html, height=340)

codigo_buscado = st.text_input(
    "Código de barras, SKU o nombre del producto:",
    placeholder="Escanea arriba o escribe el SKU / modelo (ej: BA2951, Orion, KMC)"
)

# --- 3. CONSULTA DE STOCK EN SUCURSAL TALCA Y BODEGA WEB ---
@st.cache_data(ttl=300, show_spinner=False)
def obtener_stock_talca_y_web(handle, variant_id=None):
    url = f"https://oxfordstore.cl/products/{handle}"
    if variant_id:
        url += f"?variant={variant_id}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            return "Sin info", "Sin info", {}
        
        # Limpiamos scripts, estilos y etiquetas HTML para leer el texto de sucursales
        html_limpio = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.DOTALL | re.IGNORECASE)
        texto = re.sub(r"<[^>]+>", " ", html_limpio)
        texto = re.sub(r"\s+", " ", texto)

        # Extraer Stock Tienda Oxford Talca
        match_talca = re.search(r"Tienda Oxford Talca\s*[:\-·]?\s*(.*?)\s*Calle 1 Norte", texto, re.IGNORECASE)
        stock_talca = match_talca.group(1).strip(" .·-") if match_talca else ""
        if not stock_talca or len(stock_talca) > 30:
            stock_talca = "No especificado"

        # Extraer Stock Bodega Web (Envío / Online)
        match_web = re.search(r"Bodega Web\s*[:\-·]?\s*(.*?)\s*Avenida Las Acacias", texto, re.IGNORECASE)
        stock_web = match_web.group(1).strip(" .·-") if match_web else ""
        if not stock_web or len(stock_web) > 30:
            stock_web = "No especificado"

        # Extraer otras sucursales por si se quiere consultar
        otras = {}
        for m in re.finditer(r"Tienda Oxford ([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+?)\s+(10\+\s*Unidades|[0-9]+\s*Unidades?|Última unidad|Agotado)", texto):
            suc = m.group(1).strip()
            est = m.group(2).strip()
            otras[f"Oxford {suc}"] = est

        return stock_talca, stock_web, otras
    except Exception:
        return "Error de red", "Error de red", {}

def clase_css_stock(texto_stock, disponible_json=None):
    t = texto_stock.lower()
    if "agotado" in t or "sin stock" in t:
        return "stock-no", f"🔴 {texto_stock}"
    if "última" in t or "ultima" in t or t.startswith("1 "):
        return "stock-poco", f"🟡 {texto_stock}"
    if "unidad" in t:
        return "stock-ok", f"🟢 {texto_stock}"
    if disponible_json is True:
        return "stock-ok", "🟢 Disponible"
    if disponible_json is False:
        return "stock-no", "🔴 Agotado"
    return "stock-poco", f"⚪ {texto_stock}"

# --- 4. MOTOR DE BÚSQUEDA TOTAL (MEMORIA + API + WEB) ---
def buscar_productos_total(termino):
    termino_limpio = termino.strip().lower()
    termino_sin_ceros = termino_limpio.lstrip("0")
    handles_encontrados = []

    # A) Buscar primero en todo el catálogo descargado en memoria (exacto por Barcode o SKU)
    for prod in catalogo_memoria:
        handle = prod.get("handle")
        titulo = (prod.get("title") or "").lower()
        for v in prod.get("variants", []):
            sku = str(v.get("sku") or "").strip().lower()
            bar = str(v.get("barcode") or "").strip().lower()
            bar_sin_ceros = bar.lstrip("0")
            
            if (termino_limpio in [sku, bar] or 
                (termino_sin_ceros and termino_sin_ceros in [sku, bar_sin_ceros]) or
                (len(termino_limpio) >= 4 and (termino_limpio in sku or termino_limpio in bar))):
                if handle and handle not in handles_encontrados:
                    handles_encontrados.append(handle)

    # B) Consultar API de sugerencias de Shopify (incluyendo agotados online con stock en tienda)
    url_sug = "https://oxfordstore.cl/search/suggest.json"
    params = {
        "q": termino,
        "resources[type]": "product",
        "resources[limit]": 6,
        "resources[options][unavailable_products]": "show",
        "resources[options][fields]": "title,product_type,variants.title,variants.sku,variants.barcode"
    }
    try:
        r = requests.get(url_sug, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r.status_code == 200:
            prods_api = r.json().get("resources", {}).get("results", {}).get("products", [])
            for p in prods_api:
                h = p["url"].split("?")[0].split("/products/")[-1]
                if h and h not in handles_encontrados:
                    handles_encontrados.append(h)
    except Exception:
        pass

    # C) Si aún no hay resultados, buscar por nombre en el catálogo en memoria
    if not handles_encontrados:
        palabras = termino_limpio.split()
        for prod in catalogo_memoria:
            titulo = (prod.get("title") or "").lower()
            if all(p in titulo for p in palabras):
                h = prod.get("handle")
                if h and h not in handles_encontrados:
                    handles_encontrados.append(h)
                if len(handles_encontrados) >= 6:
                    break

    return handles_encontrados[:6]

def obtener_detalle_js(handle):
    url = f"https://oxfordstore.cl/products/{handle}.js"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# --- 5. MOSTRAR RESULTADOS EN TARJETAS GRANDES ---
if codigo_buscado:
    termino = codigo_buscado.strip()
    with st.spinner(f"Buscando '{termino}' y consultando stock en Sucursal Talca..."):
        handles = buscar_productos_total(termino)

        if not handles:
            st.error(
                f"No se encontró el código **{termino}** en la base de datos web de Oxford.\n\n"
                "💡 **Tip de tienda:** Algunos repuestos traen un código de barras de fábrica (ej. Shimano/Maxxis) que no está digitado en la web, pero sí aparecen por su **código SKU corto** (impreso en la etiqueta blanca de Oxford) o por su **nombre**."
            )
        else:
            for handle in handles:
                detalle = obtener_detalle_js(handle)
                if not detalle:
                    continue

                variantes = detalle.get("variants", [])
                # Si el código escaneado coincide con una variante específica, la ponemos primero
                variantes_ordenadas = sorted(
                    variantes,
                    key=lambda v: 0 if (
                        termino.lower() in str(v.get("sku") or "").lower() or 
                        termino.lower() in str(v.get("barcode") or "").lower()
                    ) else 1
                )

                for v in variantes_ordenadas:
                    v_id = v.get("id")
                    sku_var = str(v.get("sku") or "Sin SKU")
                    bar_var = str(v.get("barcode") or "No registrado en web")
                    
                    precio_actual = int(v["price"] / 100)
                    precio_normal = int(v["compare_at_price"] / 100) if v.get("compare_at_price") else precio_actual
                    tiene_oferta = precio_normal > precio_actual
                    porcentaje_desc = int(round((1 - (precio_actual / precio_normal)) * 100)) if tiene_oferta else 0

                    # Consultamos el stock real de Talca y Bodega Web para esta variante
                    stock_talca, stock_web, otras_sucursales = obtener_stock_talca_y_web(handle, v_id)
                    clase_talca, texto_talca = clase_css_stock(stock_talca)
                    clase_web, texto_web = clase_css_stock(stock_web, v.get("available"))

                    titulo_variante = "" if v["title"] == "Default Title" else f" — {v['title']}"
                    precio_fmt = f"${precio_actual:,.0f}".replace(",", ".")
                    normal_fmt = f"${precio_normal:,.0f}".replace(",", ".")

                    html_descuento = (
                        f'<div><span class="precio-normal">Normal: {normal_fmt}</span>'
                        f'<span class="badge-descuento">-{porcentaje_desc}% OFERTA</span></div>'
                        if tiene_oferta else '<div style="color:#555; font-size:0.9rem;">Precio Normal</div>'
                    )

                    # Renderizamos la tarjeta visual grande
                    st.markdown(f"""
                    <div class="tarjeta-producto">
                        <div class="titulo-prod">{detalle['title']}{titulo_variante}</div>
                        <div class="caja-codigos">
                            <span class="badge-codigo">🏷️ SKU: {sku_var}</span>
                            <span class="badge-codigo">▮||▮ Barras: {bar_var}</span>
                        </div>
                        <div class="caja-precios">
                            {html_descuento}
                            <div class="precio-oferta">{precio_fmt}</div>
                        </div>
                        <div class="grid-stock">
                            <div class="caja-stock {clase_talca}">
                                <span class="label-sucursal">🏪 Sucursal Talca</span>
                                <span class="valor-stock">{texto_talca}</span>
                            </div>
                            <div class="caja-stock {clase_web}">
                                <span class="label-sucursal">🌐 Bodega Web (Online)</span>
                                <span class="valor-stock">{texto_web}</span>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Opcional: Desplegable rápido para ver otras tiendas o abrir el link
                    col1, col2 = st.columns(2)
                    with col1:
                        if otras_sucursales:
                            with st.expander("📍 Ver otras sucursales"):
                                for suc, est in otras_sucursales.items():
                                    st.write(f"**{suc}:** {est}")
                    with col2:
                        st.markdown(f"[🔗 Abrir en oxfordstore.cl](https://oxfordstore.cl/products/{handle}?variant={v_id})")
