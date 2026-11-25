"""
app.py - Interfaz gráfica (GUI) del conversor de divisas, hecha con Streamlit.

Este archivo solo se encarga de PINTAR y de recoger lo que hace el usuario.
Toda la lógica (API, XML y cálculo) está en bce.py.

Ejecutar con:
    streamlit run app.py
"""

import pandas as pd
import requests
import streamlit as st

import bce

st.set_page_config(page_title="Conversor de Divisas (BCE)", page_icon="💱")


# --------------------------------------------------------------------------
# 1. Carga automática de los datos al iniciar
# --------------------------------------------------------------------------
# Streamlit vuelve a ejecutar TODO el archivo cada vez que el usuario toca algo
# (escribe, cambia un desplegable, pulsa el botón...). Sin caché, cada clic
# volvería a descargar el XML del BCE.
# @st.cache_data guarda el resultado y lo reutiliza; ttl=3600 hace que se
# vuelva a descargar como mucho una vez por hora (el BCE solo publica 1 vez al día).
@st.cache_data(ttl=3600)
def cargar_datos():
    xml_bytes = bce.descargar_xml()
    fecha, tasas = bce.parsear_xml(xml_bytes)
    return xml_bytes.decode("utf-8"), fecha, tasas


st.title("💱 Conversor de Divisas (BCE)")
st.write("Esta aplicación consume **XML en tiempo real** del Banco Central Europeo.")

# Si no hay internet o el BCE falla, avisamos y paramos aquí (st.stop) en vez
# de dejar que la aplicación se rompa con un error en inglés.
try:
    xml_texto, fecha, tasas = cargar_datos()
except requests.exceptions.RequestException:
    st.error("No se ha podido conectar con el Banco Central Europeo. "
             "Revisa tu conexión a Internet y recarga la página.")
    st.stop()
except ValueError as error:  # el XML ha llegado pero no tiene el formato esperado
    st.error(f"Los datos recibidos no son válidos: {error}")
    st.stop()

with st.expander("🔍 Ver estructura XML recibida (datos en bruto)"):
    st.code(xml_texto, language="xml")

# Fecha de actualización: obligatoria según el enunciado
st.success(f"✅ Datos cargados. Fecha oficial: **{fecha}**")


# --------------------------------------------------------------------------
# 2. Formulario de conversión
# --------------------------------------------------------------------------
monedas = list(tasas.keys())  # EUR, USD, JPY, ...

col1, col2, col3 = st.columns(3)
# Usamos text_input (y no number_input) para poder validar nosotros mismos
# lo que escribe el usuario, como pide el enunciado (letras en vez de números).
texto_importe = col1.text_input("Cantidad", value="100")
origen = col2.selectbox("De:", monedas, index=monedas.index("EUR"))
destino = col3.selectbox("A:", monedas, index=monedas.index("USD"))

if st.button("Calcular conversión", type="primary"):
    try:
        importe = bce.validar_importe(texto_importe)
    except ValueError as error:
        st.error(error)
    else:  # el else de un try solo se ejecuta si NO ha habido error
        resultado = bce.convertir(importe, origen, destino, tasas)
        tipo_cambio = bce.convertir(1, origen, destino, tasas)

        st.metric(f"Valor en {destino}", f"{resultado:,.2f} {destino}")
        st.caption(
            f"{importe:,.2f} {origen} → {importe / tasas[origen]:,.4f} EUR → "
            f"{resultado:,.2f} {destino}   ·   Tipo de cambio: 1 {origen} = {tipo_cambio:.4f} {destino}"
        )


# --------------------------------------------------------------------------
# 3. Tabla con todas las tasas
# --------------------------------------------------------------------------
st.divider()
st.subheader("📊 Tabla de tipos de cambio (base EUR)")
tabla = pd.DataFrame(tasas.items(), columns=["Moneda", "1 EUR equivale a"])
st.dataframe(tabla, hide_index=True, width="stretch")
