import streamlit as st
import streamlit.components.v1 as components
import requests
import re
import json
import os
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

def guardar_vinculo(codigo_fisico, handle_destino):
    vinculos = cargar_vinculos()
    vinculos[codigo_fisico.upper()] = handle_destino
    try:
        with open(ARCHIVO_VINCULOS, "w", encoding="utf-8") as f:
            json.dump(vinculos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def limpiar_codigo_escaneado(texto):
    if not texto:
        return ""
    t = str(texto).strip()
    t = re.sub(r"^\][A-Za-z0-9]{2}", "", t)
    t = re.sub(r"[^A-Za-z0-9\-_.\s]", "", t)
    return t.strip()

estilos_css = (
    "<style>"
    ".tarjeta-producto {border:2px solid #e0e0e0; border-radius:14px; padding:16px; margin-bottom:18px; background:#ffffff; color:#111111; box-shadow:0 4px 10px rgba(0,0,0,0.06);}"
    ".titulo-prod {font-size:1.25rem; font-weight:800; color:#1a1a1a; margin-bottom:6px;}"
    ".caja-codigos {display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px;}"
    ".badge-codigo {background:#f1f3f5; color:#212529; padding:5px 10px; border-radius:6px; font-size:0.9rem; font-weight:700; border:1px solid #ced4da;}"
    ".caja-precios {background:#f8fff9; border:2px solid #2b8a3e; border-radius:10px; padding:12px; text-align:center; margin-bottom:12px;}"
    ".precio-oferta {font-size:2.2rem; font-weight:900; color:#2b8a3e; line-height:1.1;}"
    ".precio-normal {font-size:1.05rem; color:#868e96; text-decoration:line-through; margin-right:8px;}"
    ".badge-descuento {background:#e03131; color:white; padding:3px 8px; border-radius:6px; font-weight:800; font-size:0.9rem;}"
    ".grid-stock {display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px;}"
    ".caja-stock {padding:10px; border-radius:8px; text-align:center; font-weight:700;}"
    ".stock-ok {background:#ebfbee; border:2px solid #40c057; color:#1b4332;}"
    ".stock-poco {background:#fff9db; border:2px solid #fab005; color:#5c3c00;}"
    ".stock-no {background:#fff5f5; border:2px solid #fa5252; color:#7f1d1d;}"
    ".label-sucursal {font-size:0.8rem; text-transform:uppercase; opacity:0.85; display:block;}"
    ".valor-stock {font-size:1.15rem; font-weight:900; display:block; margin-top:2px;}"
    "</style>"
)
st.markdown(estilos_css, unsafe_allow_html=True)

st.title("🚲 Verificador Oxford — Sucursal Talca")

@st.cache_data(ttl=1800, show_spinner=False)
def cargar_catalogo_oxford():
    urls = [
        f"https://oxfordstore.cl/collections/bicicletas/products.json?limit=250&page={p}"
        for p in range(1, 4)
    ] + [
        f"https://oxfordstore.cl/products.json?limit=250&page={p}"
        for p in range(1, 10)
    ]

    def descargar_pagina(url):
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=7)
            if r.status_code == 200:
                return r.json().get("products", [])
        except Exception:
            pass
        return []

    catalogo_dict = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        for lista_prods in executor.map(descargar_pagina, urls):
            for p in lista_prods:
                h = p.get("handle")
                if h and h not in catalogo_dict:
                    catalogo_dict[h] = {
                        "handle": h,
                        "title": str(p.get("title") or ""),
                        "product_type": str(p.get("product_type") or ""),
                        "variants": [
                            {
                                "id": v.get("id"),
                                "title": str(v.get("title") or ""),
                                "sku": str(v.get("sku") or "").strip(),
                                "barcode": str(v.get("barcode") or "").strip(),
                            }
                            for v in p.get("variants", [])
                        ],
                    }
    return list(catalogo_dict.values())

with st.spinner("Sincronizando bicicletas, repuestos y accesorios de Oxford Store..."):
    catalogo_memoria = cargar_catalogo_oxford()

escaner_hd_html = (
    '<script src="https://unpkg.com/html5-qrcode"></script>'
    '<div style="text-align:center; font-family:sans-serif;">'
    '  <div id="reader" style="width:100%; max-width:450px; margin:auto; border-radius:12px; overflow:hidden; border:2px solid #333;"></div>'
    '  <div style="margin-top:8px; display:flex; justify-content:center; gap:10px; align-items:center; flex-wrap:wrap;">'
    '    <label style="font-size:13px; font-weight:bold;">🔍 Zoom:'
    '      <input id="zoom-slider" type="range" min="1" max="3" step="0.2" value="1.5" oninput="aplicarZoom(this.value)" style="vertical-align:middle; width:110px;">'
    '    </label>'
    '    <button id="btn-flash" onclick="toggleFlash()" style="padding:6px 12px; border-radius:6px; border:1px solid #555; background:#222; color:#fff; font-size:13px; cursor:pointer;">🔦 Linterna</button>'
    '    <button id="btn-reiniciar" onclick="iniciarCamara()" style="display:none; padding:6px 14px; border:none; border-radius:6px; background:#0066cc; color:white; font-weight:bold; font-size:13px; cursor:pointer;">🔄 Escanear otro</button>'
    '  </div>'
    '  <div id="estado" style="margin-top:
