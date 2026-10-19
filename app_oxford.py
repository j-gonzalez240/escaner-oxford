import streamlit as st
import requests
from PIL import Image
from streamlit_qrcode_scanner import qrcode_scanner

st.set_page_config(page_title="Escáner Oxford", page_icon="🚲", layout="centered")

st.title("🚲 Escáner y Consulta Oxford")

# Creamos 3 pestañas para que uses el método más cómodo en la tienda
tab_vivo, tab_foto, tab_manual = st.tabs([
    "📷 Escáner en Vivo", 
    "📸 Foto al Código", 
    "⌨️ Escribir Manual"
])

codigo_buscado = None

# 1. ESCÁNER EN TIEMPO REAL
with tab_vivo:
    st.caption("Apunta con la cámara al código de barras o QR:")
    codigo_vivo = qrcode_scanner(key="lector_en_vivo")
    if codigo_vivo:
        st.success(f"Código detectado: {codigo_vivo}")
        codigo_buscado = codigo_vivo

# 2. CÁMARA NATIVA DE STREAMLIT (Ideal si la etiqueta es pequeña o cuesta enfocar)
with tab_foto:
    st.caption("Toma una foto de cerca al código de barras:")
    imagen_capturada = st.camera_input("Capturar etiqueta")
    if imagen_capturada is not None:
        img_pil = Image.open(imagen_capturada)
        codigos = zxingcpp.read_barcodes(img_pil)
        if codigos:
            codigo_foto = codigos[0].text
            st.success(f"Código leído: {codigo_foto}")
            codigo_buscado = codigo_foto
        else:
            st.error("No se distinguió el código. Acerca más la cámara a las barras e intenta de nuevo.")

# 3. BÚSQUEDA MANUAL POR TEXTO O SKU
with tab_manual:
    texto_manual = st.text_input(
        "Ingresa el SKU, código de barras o modelo:", 
        placeholder="Ej: BA2951, Merak 1 o código de 13 dígitos"
    )
    if texto_manual:
        codigo_buscado = texto_manual.strip()

# --- FUNCIONES DE CONSULTA A OXFORDSTORE.CL ---
def buscar_en_oxford(termino):
    url_busqueda = "https://oxfordstore.cl/search/suggest.json"
    params = {
        "q": termino,
        "resources[type]": "product",
        "resources[limit]": 5,
        # Indicamos a Shopify que busque específicamente en título, SKU y código de barras
        "resources[options][fields]": "title,variants.sku,variants.barcode"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    resp = requests.get(url_busqueda, params=params, headers=headers)
    if resp.status_code != 200:
        return []
    
    datos = resp.json()
    return datos.get("resources", {}).get("results", {}).get("products", [])

def obtener_detalle_producto(handle):
    url_producto = f"https://oxfordstore.cl/products/{handle}.js"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url_producto, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return None

# --- MOSTRAR RESULTADOS AUTOMÁTICAMENTE ---
if codigo_buscado:
    with st.spinner(f"Buscando '{codigo_buscado}' en oxfordstore.cl..."):
        resultados = buscar_en_oxford(codigo_buscado)
        
        if not resultados:
            st.warning("No apareció con el código de barras largo. Intenta escanear o escribir el código SKU corto de la etiqueta.")
        else:
            for item in resultados:
                url_limpia = item["url"].split("?")[0]
                handle = url_limpia.split("/products/")[-1]
                
                detalle = obtener_detalle_producto(handle)
                if detalle:
                    with st.container(border=True):
                        st.subheader(detalle["title"])
                        
                        filas = []
                        for v in detalle.get("variants", []):
                            precio_actual = int(v["price"] / 100)
                            precio_normal = int(v["compare_at_price"] / 100) if v.get("compare_at_price") else precio_actual
                            
                            # Destacar con una flecha la fila que coincide exactamente con lo escaneado
                            sku_var = str(v.get("sku") or "")
                            bar_var = str(v.get("barcode") or "")
                            coincide = "👉 " if (codigo_buscado in [sku_var, bar_var]) else ""
                            
                            filas.append({
                                "Variante": f"{coincide}{v['title']}",
                                "SKU": sku_var if sku_var else "N/A",
                                "Cód. Barras": bar_var if bar_var else "No reg.",
                                "Oferta": f"${precio_actual:,.0f}".replace(",", "."),
                                "Normal": f"${precio_normal:,.0f}".replace(",", "."),
                                "Web": "✅ Disp." if v["available"] else "❌ Agotado"
                            })
                        
                        st.table(filas)
                        st.markdown(f"[🔗 Ver disponibilidad por sucursal en Oxford Store](https://oxfordstore.cl{url_limpia})")
