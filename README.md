# 💱 Conversor de Divisas (BCE)

Práctica PrDesafio03 — Accés a dades (MP0486), 2º DAM, Centre d'Estudis Monlau.
Autor: Enrique Flores

Aplicación en **Streamlit** que descarga al iniciar los tipos de cambio oficiales del
**Banco Central Europeo** en formato **XML**, los procesa con `xml.etree.ElementTree`
y permite convertir cantidades entre cualquier par de monedas.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador (`http://localhost:8501`). Necesita conexión a Internet.

## Estructura

```
├── bce.py            # Lógica: API (descarga), XML (parsing) y cálculo
├── app.py            # Interfaz gráfica con Streamlit
├── requirements.txt  # requests, streamlit, pandas
└── README.md
```

Separo la lógica (`bce.py`) de la interfaz (`app.py`): así cada parte se entiende por
separado y `bce.py` serviría igual con Tkinter.

## Flujo de datos

```
Iniciar app ──► GET a la URL del BCE ──► XML ──► ElementTree ──► fecha + {moneda: tasa}
                                                                        │
     Resultado ◄── convertir(importe, origen, destino) ◄── formulario ◄─┘
```

1. **API** (`descargar_xml`): `requests.get` con `timeout=10` y `raise_for_status()`.
2. **XML** (`parsear_xml`): busco el `<Cube time="...">` para la fecha y recorro sus
   hijos `<Cube currency="..." rate="...">` para las tasas.
3. **Cálculo** (`convertir`): conversión cruzada usando el Euro como puente.

## La conversión cruzada

Todas las tasas del BCE significan **1 EUR = tasa monedas**. Para convertir entre dos
monedas que no son el Euro, paso primero por euros:

```
cantidad_final = (importe / tasa_origen) × tasa_destino
```

Ejemplo: 100 USD → JPY (USD = 1,1648 · JPY = 179,22)
`100 / 1,1648 = 85,85 EUR` → `85,85 × 179,22 = 15.386,33 JPY`

El XML **no trae el Euro** (es la moneda base), así que lo añado a mano con tasa `1.0`.
Con eso, convertir desde o hacia EUR usa la misma fórmula sin casos especiales.

## Decisiones técnicas y problemas resueltos

- **Namespace del XML**: el documento declara un namespace por defecto
  (`xmlns="http://www.ecb.int/..."`), así que buscar `"Cube"` a secas no encuentra nada.
  Lo resuelvo con el diccionario `NAMESPACE` y búsquedas tipo `"ecb:Cube"`.
- **XPath `.//ecb:Cube[@time]`**: localiza directamente el único `Cube` con fecha,
  sin depender de cuántos niveles haya por encima.
- **Atributos a número**: `rate` llega como texto y lo paso a `float`.
- **Validación del importe**: uso un `text_input` en lugar de `number_input` para validar
  yo mismo la entrada. Acepto coma decimal (`25,50`) y muestro un error si hay letras o
  si la cantidad es negativa.
- **Caché** (`@st.cache_data(ttl=3600)`): Streamlit reejecuta el script en cada clic;
  así el XML se descarga una vez y no en cada interacción.
- **Errores de red**: si no hay conexión, la app muestra un aviso y se detiene (`st.stop()`)
  en lugar de romperse.
