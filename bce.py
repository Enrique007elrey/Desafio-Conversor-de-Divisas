"""
bce.py - Lógica de negocio del conversor de divisas.

Aquí NO hay nada de interfaz gráfica: solo las tres tareas de la práctica,
cada una en su función para que se puedan entender y probar por separado.

    1. API   -> descargar_xml()   : petición HTTP GET al Banco Central Europeo
    2. XML   -> parsear_xml()     : sacar la fecha y las tasas del árbol XML
    3. Mates -> convertir()       : conversión cruzada usando el Euro como puente

Separarlo de app.py (la interfaz) hace que, si mañana cambiamos Streamlit por
Tkinter, este archivo se pueda reutilizar sin tocar ni una línea.
"""

import xml.etree.ElementTree as ET

import requests

# URL pública del BCE: se actualiza cada día laborable sobre las 16:00 (hora CET)
URL_BCE = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

# El XML usa un "espacio de nombres" (namespace) por defecto. Por eso las
# etiquetas <Cube> en realidad se llaman "{http://www.ecb.int/...}Cube" y,
# si buscamos solo "Cube", ElementTree no encuentra NADA.
# Con este diccionario le damos un apodo corto ("ecb") a ese namespace.
NAMESPACE = {"ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}


# --------------------------------------------------------------------------
# 1. API: descargar el XML
# --------------------------------------------------------------------------
def descargar_xml() -> bytes:
    """Hace una petición GET al BCE y devuelve el XML tal cual (en bytes).

    - timeout=10: si el servidor no responde en 10 s, salta un error en vez
      de dejar la aplicación colgada.
    - raise_for_status(): si el servidor contesta con un error (404, 500...),
      lanza una excepción. Así no intentamos parsear una página de error.
    Devolvemos .content (bytes) y no .text porque ElementTree lee la
    codificación directamente de la cabecera <?xml ... encoding="UTF-8"?>.
    """
    respuesta = requests.get(URL_BCE, timeout=10)
    respuesta.raise_for_status()
    return respuesta.content


# --------------------------------------------------------------------------
# 2. XML: extraer la fecha y las tasas
# --------------------------------------------------------------------------
def parsear_xml(xml_bytes: bytes) -> tuple[str, dict[str, float]]:
    """Recorre el árbol XML y devuelve (fecha, {moneda: tasa}).

    Estructura del XML (resumida):
        <gesmes:Envelope>
            <Cube>                                  <- nivel 1 (contenedor)
                <Cube time="2026-11-25">            <- nivel 2 (la fecha)
                    <Cube currency="USD" rate="1.16"/>   <- nivel 3 (monedas)
                    <Cube currency="JPY" rate="179.2"/>
                    ...
    """
    raiz = ET.fromstring(xml_bytes)  # convierte el texto XML en un árbol

    # ".//ecb:Cube[@time]" = busca en cualquier nivel (.//) un <Cube> que
    # tenga el atributo time. Solo hay uno: el que lleva la fecha.
    cubo_fecha = raiz.find(".//ecb:Cube[@time]", NAMESPACE)
    if cubo_fecha is None:
        raise ValueError("El XML no tiene el formato esperado (no hay fecha).")
    fecha = cubo_fecha.get("time")

    # El XML no incluye el Euro porque TODAS las tasas son "1 EUR = X moneda".
    # Lo añadimos a mano con valor 1.0 para poder convertir desde/hacia EUR.
    tasas = {"EUR": 1.0}

    # Los hijos de cubo_fecha son los <Cube currency="..." rate="..."/>
    for cubo in cubo_fecha.findall("ecb:Cube", NAMESPACE):
        moneda = cubo.get("currency")
        tasa = float(cubo.get("rate"))  # el atributo es texto: lo pasamos a número
        tasas[moneda] = tasa

    return fecha, tasas


# --------------------------------------------------------------------------
# 3. Matemáticas: validar y convertir
# --------------------------------------------------------------------------
def validar_importe(texto: str) -> float:
    """Convierte lo que escribe el usuario en un número válido.

    - Acepta coma decimal ("100,50"), que es como escribimos en España.
    - Si hay letras, float() lanza ValueError y lo cambiamos por un mensaje claro.
    - No tiene sentido convertir cantidades negativas.
    """
    texto = texto.strip().replace(",", ".")
    try:
        importe = float(texto)
    except ValueError:
        raise ValueError("Introduce un número válido (por ejemplo 100 o 25,50).")
    if importe < 0:
        raise ValueError("La cantidad no puede ser negativa.")
    return importe


def convertir(importe: float, origen: str, destino: str, tasas: dict[str, float]) -> float:
    """Conversión cruzada usando el Euro como moneda puente.

    Todas las tasas son "1 EUR = tasa moneda", así que:
        1) importe / tasa_origen   -> pasamos la cantidad a EUROS
        2) euros * tasa_destino    -> pasamos los euros a la moneda destino

    Ejemplo: 100 USD a JPY con USD=1.1648 y JPY=179.22
        100 / 1.1648 = 85.85 EUR  ->  85.85 * 179.22 = 15.386,33 JPY

    Si el origen es EUR, tasa_origen = 1 y el paso 1 no cambia nada:
    por eso añadimos el Euro con valor 1.0.
    """
    euros = importe / tasas[origen]
    return euros * tasas[destino]
