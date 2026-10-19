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

st.markdown(r"""
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
