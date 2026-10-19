import streamlit as st
import streamlit.components.v1 as components
import requests, re, json, os
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Verificador Oxford Talca", page_icon="🚲", layout="centered")
ARCHIVO_VINCULOS = "codigos_tienda_talca.json"

def cargar_vinculos():
    if os.path.exists(ARCHIVO_VINCULOS):
        try:
            with open(ARCHIVO_VINCULOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_vinculo(cod, handle):
    v = cargar_vinculos()
    v[cod.upper()] = handle
    try:
        with open(ARCHIVO_VINCULOS, "w", encoding="utf-8") as f:
            json.dump(v, f)
    except Exception:
        pass

def limpiar_codigo(t):
    t = str(t or "").strip()
    if t.startswith("]") and len(t) > 3:
        t = t[3:]
    return re.sub(r"[^A-Za-z0-9\-_.\s]", "", t).strip()

st.title("🚲 Verificador Oxford — Sucursal Talca")

@st.cache_data(ttl=1800, show_spinner=False)
def cargar_catalogo():
    urls = [f"https://oxfordstore.cl/collections/bicicletas/products.json?limit=250&page={p}" for p in range(1, 4)]
    urls += [f"https://oxfordstore.cl/products.json?limit=250&page={p}" for p in range(1, 10)]
    def bajar(u):
        try:
            r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=7)
            return r.json().get("products", []) if r.status_code == 200 else []
        except Exception:
            return []
    cat = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for prods in ex.map(bajar, urls):
            for p in prods:
                h = p.get("handle")
                if h and h not in cat:
                    cat[h] = {
                        "handle": h,
                        "title": str(p.get("title") or ""),
                        "variants": [
                            {"id": v.get("id"), "title": str(v.get("title") or ""),
                             "sku": str(v.get("sku") or "").strip(), "barcode": str(v.get("barcode") or "").strip()}
                            for v in p.get("variants", [])
                        ]
                    }
    return list(cat.values())

with st.spinner("Sincronizando bicicletas, repuestos y accesorios..."):
    catalogo_memoria = cargar_catalogo()

escaner_html = """
<script src="https://unpkg.com/html5-qrcode"></script>
<div style="text-align:center;font-family:sans-serif;color:#eee;">
  <div id="reader" style="width:100%;max-width:440px;margin:auto;border-radius:10px;overflow:hidden;border:2px solid #444;"></div>
  <div style="margin-top:8px;display:flex;justify-content:center;gap:8px;align-items:center;flex-wrap:wrap;">
    <label style="font-size:13px;font-weight:bold;">🔍 Zoom: <input type="range" min="1" max="3" step="0.2" value="1.5" oninput="zoomCam(this.value)" style="width:100px;vertical-align:middle;"></label>
    <button onclick="flashCam()" style="padding:5px 10px;border-radius:6px;background:#222;color:#fff;border:1px solid #666;">🔦 Linterna</button>
    <button id="btn-re" onclick="initCam()" style="display:none;padding:5px 12px;border-radius:6px;background:#0066cc;color:#fff;border:none;font-weight:bold;">🔄 Escanear otro</button>
  </div>
  <div id="est" style="margin-top:6px;font-weight:bold;color:#40c057;font-size:14px;">📷 Apunta al código a ~15 cm</div>
</div>
<script>
let qr, flash=false, ult="", cont=0;
function track(){ const v=document.querySelector("#reader video"); return (v && v.srcObject) ? v.srcObject.getVideoTracks()[0] : null; }
function zoomCam(val){ const t=track(); if(t) t.applyConstraints({advanced:[{zoom:parseFloat(val)}]}).catch(()=>{}); }
function flashCam(){ const t=track(); if(t){ flash=!flash; t.applyConstraints({advanced:[{torch:flash}]}).catch(()=>{}); } }
function enviar(cod){
  const inp = window.parent.document.querySelector('input[aria-label="Código de barras, SKU o nombre:"]');
  if(!inp) return;
  Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, "value").set.call(inp, cod);
  inp.dispatchEvent(new Event("input", {bubbles:true})); inp.focus();
  setTimeout(()=>{ inp.dispatchEvent(new window.parent.KeyboardEvent("keydown",{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true})); inp.blur(); }, 60);
}
function initCam(){
  ult=""; cont=0; document.getElementById("btn-re").style.display="none";
  qr = new Html5Qrcode("reader", {experimentalFeatures:{useBarCodeDetectorIfSupported:true}});
  const cfg = {fps:15, qrbox:{width:270,height:110}, videoConstraints:{facingMode:{exact:"environment"},width:{ideal:1920},height:{ideal:1080}}};
  qr.start({facingMode:"environment"}, cfg, (txt)=>{
    let c = txt.startsWith("]") ? txt.slice(3).trim() : txt.trim();
    if(!c) return;
    cont = (c===ult) ? cont+1 : 1; ult = c;
    if(cont>=2){ document.getElementById("est").innerText="✅ Leído: "+c; document.getElementById("btn-re").style.display="inline-block"; enviar(c); qr.stop(); }
  }, ()=>{}).then(()=>setTimeout(()=>zoomCam(1.5),500)).catch(()=>{ document.getElementById("est").innerText="⚠️ Activa el permiso de cámara"; });
}
initCam();
</script>
"""

with st.expander("📷 Escáner Cámara Trasera HD (Zoom + Linterna)", expanded=True):
    components.html(escaner_html, height=330)

with st.expander("🚲 Selección Rápida de Bicicletas y Productos"):
    mapa_opciones = {"-- Selecciona una bicicleta o producto --": ""}
    for p in catalogo_memoria:
        skus = ", ".join([v["sku"] for v in p["variants"] if v["sku"]])
        mapa_opciones[f"{p['title']} ({skus})" if skus else p["title"]] = p["handle"]
    seleccion_rapida = st.selectbox("Listado completo:", list(mapa_opciones.keys()))

entrada_usuario = st.text_input("Código de barras, SKU o nombre:", placeholder="Ej: BA2951, Merak 1, Casco, Guantes")

@st.cache_data(ttl=300, show_spinner=False)
def obtener_stock(handle, v_id=None):
    url = f"https://oxfordstore.cl/products/{handle}" + (f"?variant={v_id}" if v_id else "")
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return "Sin info", "Sin info"
        limpio = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.DOTALL | re.IGNORECASE)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", limpio))
        m_t = re.search(r"Tienda Oxford Talca\s*[:\-·]?\s*(.*?)\s*Calle 1 Norte", txt, re.IGNORECASE)
        m_w = re.search(r"Bodega Web\s*[:\-·]?\s*(.*?)\s*Avenida Las Acacias", txt, re.IGNORECASE)
        st_t = m_t.group(1).strip(" .·-") if m_t else "Consultar"
        st_w = m_w.group(1).strip(" .·-") if m_w else "Consultar"
        return (st_t if len(st_t) < 28 else "Consultar"), (st_w if len(st_w) < 28 else "Consultar")
    except Exception:
        return "Error red", "Error red"

def buscar_total(termino):
    t = limpiar_codigo(termino).lower()
    t_sin0 = t.lstrip("0")
    res = []
    vinc = cargar_vinculos()
    if t.upper() in vinc:
        t = vinc[t.upper()].lower()
    m_sku = re.search(r"\b([a-z]{2}\d{4})\b", t)
    p_sku = m_sku.group(1) if m_sku else None

    for p in catalogo_memoria:
        h = p["handle"]
        if h == t and h not in res:
            res.append(h)
        for v in p["variants"]:
            s, b = v["sku"].lower(), v["barcode"].lower()
            if t in [s, b] or (p_sku and p_sku == s) or (t_sin0 and t_sin0 in [s, b.lstrip("0")]) or (len(t) >= 4 and ((s and t in s) or (b and t in b))):
                if h not in res:
                    res.append(h)

    try:
        r = requests.get("https://oxfordstore.cl/search/suggest.json", params={"q": limpiar_codigo(termino), "resources[type]": "product", "resources[options][unavailable_products]": "show", "resources[options][fields]": "title,product_type,variants.title,variants.sku,variants.barcode"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r.status_code == 200:
            for p in r.json().get("resources", {}).get("results", {}).get("products", []):
                h = p["url"].split("?")[0].split("/products/")[-1]
                if h and h not in res:
                    res.append(h)
    except Exception:
        pass

    if not res:
        palabras = [w for w in t.split() if len(w) > 1]
        for p in catalogo_memoria:
            if palabras and all(w in p["title"].lower() for w in palabras):
                if p["handle"] not in res:
                    res.append(p["handle"])
    return res[:6]

cod_activo = limpiar_codigo(entrada_usuario)
h_directo = mapa_opciones.get(seleccion_rapida, "")

if cod_activo or h_directo:
    with st.spinner("Consultando precio y stock en Sucursal Talca..."):
        handles = buscar_total(cod_activo) if cod_activo else [h_directo]
        if not handles:
            st.warning(f"No se encontró `{cod_activo}` en el catálogo web. Si es un número de chasis (`OX...`) o código interno, vincúlalo abajo:")
            prod_vinc = st.selectbox("Asociar este código a:", list(mapa_opciones.keys()))
            if st.button("💾 Guardar vínculo y ver precio"):
                if mapa_opciones.get(prod_vinc):
                    guardar_vinculo(cod_activo, mapa_opciones[prod_vinc])
                    st.rerun()
        else:
            for h in handles:
                r_js = requests.get(f"https://oxfordstore.cl/products/{h}.js", headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
                if r_js.status_code != 200:
                    continue
                det = r_js.json()
                vars_ord = sorted(det.get("variants", []), key=lambda v: 0 if (cod_activo and (cod_activo.lower() in str(v.get("sku") or "").lower() or cod_activo.lower() in str(v.get("barcode") or "").lower())) else 1)
                for v in vars_ord:
                    vid = v.get("id")
                    sku_v = v.get("sku") or "Sin SKU"
                    bar_v = v.get("barcode") or "No reg."
                    p_act = int(v["price"] / 100)
                    p_nor = int(v["compare_at_price"] / 100) if v.get("compare_at_price") else p_act
                    st_talca, st_web = obtener_stock(h, vid)
                    t_var = "" if v["title"] == "Default Title" else f" — {v['title']}"

                    with st.container(border=True):
                        st.subheader(f"{det['title']}{t_var}")
                        st.caption(f"🏷️ **SKU:** `{sku_v}`  |  ▮||▮ **Barras:** `{bar_v}`")
                        if p_nor > p_act:
                            desc = int(round((1 - p_act / p_nor) * 100))
                            st.markdown(f"Normal: ~~${p_nor:,.0f}~~  🔥 **-{desc}% OFERTA**".replace(",", "."))
                        st.markdown(f"<h1 style='color:#2ecc71;margin:0;'>${p_act:,.0f}</h1>".replace(",", "."), unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        c1.metric("🏪 Sucursal Talca", st_talca)
                        c2.metric("🌐 Bodega Web", st_web if st_web != "Consultar" else ("Disponible" if v.get("available") else "Agotado"))
                        st.markdown(f"[🔗 Ver ficha en oxfordstore.cl](https://oxfordstore.cl/products/{h}?variant={vid})")
# === FIN DEL CODIGO ===
