import streamlit as st
import streamlit.components.v1 as components
import requests

st.set_page_config(page_title="Escáner Oxford", page_icon="🚲", layout="centered")

st.title("🚲 Escáner y Consulta Oxford")

# Lector configurado con facingMode: "environment" (obliga a usar la cámara trasera)
escaner_trasero_html = """
<script src="https://unpkg.com/html5-qrcode"></script>
<div style="text-align: center; font-family: sans-serif;">
  <div id="reader" style="width: 100%; max-width: 420px; margin: auto; border-radius: 10px; overflow: hidden;"></div>
  <div id="estado" style="margin-top: 8px; font-weight: bold; color: #00a650; font-size: 15px;">
    📷 Apunta con la cámara trasera al código
  </div>
  <button id="btn-reiniciar" onclick="iniciarCamara()" style="display:none; margin-top:8px; padding:8px 16px; border:none; border-radius:6px; background:#0066cc; color:white; font-size:14px; cursor:pointer;">
    🔄 Escanear otro código
  </button>
</div>

<script>
  let html5QrCode;

  function enviarAStreamlit(codigo) {
    try {
      const parentDoc = window.parent.document;
      const input = parentDoc.querySelector('input[aria-label="Código o nombre del producto:"]');
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
        }, 50);
      }
    } catch (e) {
      console.log("Error enviando al input:", e);
    }
  }

  function iniciarCamara() {
    document.getElementById("btn-reiniciar").style.display = "none";
    document.getElementById("estado").innerText = "📷 Apunta con la cámara trasera al código";
    
    html5QrCode = new Html5Qrcode("reader");
    html5QrCode.start(
      { facingMode: "environment" }, // Fuerza la cámara principal trasera
      { fps: 10, qrbox: { width: 250, height: 110 } },
      (decodedText) => {
        document.getElementById("estado").innerText = "✅ Código leído: " + decodedText;
        document.getElementById("btn-reiniciar").style.display = "inline-block";
        enviarAStreamlit(decodedText);
        html5QrCode.stop();
      },
      (errorMessage) => {}
    ).catch((err) => {
      document.getElementById("estado").innerText = "⚠️ Da permiso a la cámara en tu navegador.";
    });
  }

  iniciarCamara();
</script>
"""

with st.expander("📷 Abrir Escáner de Cámara Trasera", expanded=True):
    components.html(escaner_trasero_html, height=300)

# Cuadro de búsqueda (se rellena solo al escanear o puedes escribir a mano)
codigo_buscado = st.text_input(
    "Código o nombre del producto:",
    placeholder="Escanea arriba o escribe el SKU / modelo (ej: BA2951 o Merak 1)"
)

# --- FUNCIONES DE CONSULTA A OXFORDSTORE.CL ---
def buscar_en_oxford(termino):
    url_busqueda = "https://oxfordstore.cl/search/suggest.json"
    params = {
        "q": termino,
        "resources[type]": "product",
        "resources[limit]": 5,
        "resources[options][fields]": "title,variants.sku,variants.barcode"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url_busqueda, params=params, headers=headers)
    if resp.status_code != 200:
        return []
    return resp.json().get("resources", {}).get("results", {}).get("products", [])

def obtener_detalle_producto(handle):
    url_producto = f"https://oxfordstore.cl/products/{handle}.js"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url_producto, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return None

# --- MOSTRAR RESULTADOS AUTOMÁTICAMENTE ---
if codigo_buscado:
    termino = codigo_buscado.strip()
    with st.spinner(f"Buscando '{termino}' en oxfordstore.cl..."):
        resultados = buscar_en_oxford(termino)
        
        if not resultados:
            st.warning("No apareció con ese código exacto. Intenta con el código SKU corto de la etiqueta o el nombre del modelo.")
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
                            
                            sku_var = str(v.get("sku") or "")
                            bar_var = str(v.get("barcode") or "")
                            coincide = "👉 " if (termino in [sku_var, bar_var]) else ""
                            
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
