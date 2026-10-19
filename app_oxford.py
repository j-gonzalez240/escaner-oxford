import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import json
import os

st.set_page_config(page_title="Verificador Oxford Talca", page_icon="🚲", layout="centered")

# --- ARCHIVO LOCAL PARA VINCULAR CÓDIGOS DE CHASIS (OX...) O ETIQUETAS DE TIENDA ---
ARCHIVO_VINCULOS = "codigos_tienda_talca.json"

def cargar_vinculos():
    if os.path.exists(ARCHIVO_VINCULOS):
        try:
            with open(ARCHIVO_VINCULOS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_vinculo(codigo_fisico, sku_o_handle):
    vinculos = cargar_vinculos()
    vinculos[codigo_fisico.upper()] = sku_o_handle
    try:
        with open(ARCHIVO_VINCULOS, "w", encoding="utf-8") as f:
            json.dump(vinculos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# --- FUNCIÓN PARA LIMPIAR PREFIJOS DEL ESCÁNER COMO ]C1, ]C0, ]E0 ---
def limpiar_codigo_escaneado(texto):
    if not texto:
        return ""
    # 1. Quitar prefijos AIM de lectores de barras (ej: ]C1, ]C0, ]E0, ]I1, ]d2)
    limpio = re.sub(r"^\][A-Za-z0-9]{2}", "", str(texto).strip())
    # 2. Quitar caracteres invisibles de control GS1 (ASCII 0-31)
    limpio = re.sub(r"[\x00-\x1F\x7F]", "", limpio).strip()
    return limpio

# --- ESTILOS VISUALES PARA CELULAR ---
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

# --- 1. CARGA COMPLETA: COLECCIÓN BICICLETAS + CATÁLOGO DE TIENDA ---
@st.cache_data(ttl=1800, show_spinner=False)
def cargar_catalogo_oxford():
    catalogo_dict = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # A) Primero aseguramos TODAS las bicicletas de Oxford
    for pag in range(1, 5):
        try:
            url_bicis = f"https://oxfordstore.cl/collections/bicicletas/products.json?limit=250&page={pag}"
            r = requests.get(url_bicis, headers=headers, timeout=8)
            if r.status_code != 200:
                break
            prods = r.json().get("products", [])
            if not prods:
                break
            for p in prods:
                catalogo_dict[p["handle"]] = p
        except Exception:
            break

    # B) Luego cargamos el catálogo general (repuestos, cascos, guantes, ropa, accesorios)
    for pag in range(1, 12):
        try:
            url_gen = f"https://oxfordstore.cl/products.json?limit=250&page={pag}"
            r = requests.get(url_gen, headers=headers, timeout=8)
            if r.status_code != 200:
                break
            prods = r.json().get("products", [])
            if not prods:
                break
            for p in prods:
                catalogo_dict[p["handle"]] = p
        except Exception:
            break

    return list(catalogo_dict.values())

with st.spinner("Sincronizando bicicletas, repuestos y accesorios de Oxford Store..."):
    catalogo_memoria = cargar_catalogo_oxford()

# --- 2. ESCÁNER HD CON LIMPIEZA AUTOMÁTICA DE ]C1 ---
escaner_hd_html = """
<script src="https://unpkg.com/html5-qrcode"></script>
<div style="text-align: center; font-family: sans-serif;">
  <div id="reader" style="width: 100%; max-width: 450px; margin: auto; border-radius: 12px; overflow: hidden; border: 2px solid #333;"></div>
  
  <div id="controles-camara" style="margin-top: 8px; display: flex; justify-content: center; gap: 10px; align-items: center; flex-wrap: wrap;">
    <label style="font-
