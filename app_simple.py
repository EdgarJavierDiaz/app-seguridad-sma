
import sys
import os
import streamlit as st
import requests
import unidecode    
import pandas as pd
from datetime import datetime
from PIL import Image

# ---------------- FUNCIONES AUXILIARES ----------------
def resource_path(relative_path):
    """Obtiene la ruta de un recurso, funciona para dev y para PyInstaller"""
    import sys, os
    try:
        base_path = sys._MEIPASS  # carpeta temporal creada por el exe
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Definición de rutas de imágenes
imagen_decalogo = resource_path("Decalogo.png")
imagen_logo = resource_path("logo_empresa.png")
icono_colombia = resource_path("Colombia.ico")




# Configuración de la página
st.set_page_config(
    page_title="Seguridad SMA",
    page_icon=resource_path("Colombia.ico")  # Usa resource_path para el ícono
)

# ---------------- Funciones ----------------

def cargar_diccionario_municipios():
    try:
        df = pd.read_csv(resource_path("municipios_departamentos.csv"))
        df["DEPARTAMENTO"] = df["DEPARTAMENTO"].str.strip()
        df["MUNICIPIO"] = df["MUNICIPIO"].str.strip()
        return dict(zip(df["MUNICIPIO"], df["DEPARTAMENTO"]))
    except Exception as e:
        st.error(f"Error al cargar el diccionario de municipios: {e}")
        return {}

def mostrar_logo_sidebar():
    with st.sidebar:
        st.image(resource_path("logo_empresa.png"), width=200)
        st.markdown("---")
        ciudad = st.text_input("Ciudad", placeholder="Ej: Medellín", key="ciudad_input")
        consultar = st.button("🔍 Consultar", key="consultar_btn", use_container_width=True)
    return ciudad, consultar

def estilos_personalizados():
    
    st.markdown("# Aplicativo Ciudades Colombia")
    st.markdown("Consulta el clima, estado de vías y noticias de orden público en cualquier ciudad.")

def obtener_clima(ciudad, key):
    if not ciudad or not key:
        st.warning("No se puede consultar el clima: falta ciudad o clave de API.")
        return

    url = f"http://api.weatherapi.com/v1/current.json?key={key}&q={ciudad}&lang=es"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "current" in data:
            c = data["current"]
            col1, col2, col3 = st.columns(3)
            col1.metric("🌤 Condición", c["condition"]["text"])
            col2.metric("🌡 Temperatura", f"{c['temp_c']} °C")
            col3.metric("💧 Humedad", f"{c['humidity']} %")
        else:
            st.warning("No se pudo obtener el clima.")
    except requests.RequestException as e:
        st.error(f"Error de conexión: {e}")
    except Exception as e:
        st.error(f"Error inesperado: {e}")

def obtener_fuentes_por_ciudad(ciudad):
    ciudad = ciudad.lower()
    fuentes_generales = [
        "https://www.eltiempo.com/rss/colombia.xml",
        "https://www.elespectador.com/rss/colombia/",
        "https://colombia.as.com/rss/seguridad.xml",
        "https://www.kienyke.com/feed",
        "https://elnuevosiglo.com.co/rss.xml"
    ]

    fuentes_por_ciudad = {
        "bogotá": [
            "https://www.eltiempo.com/rss/bogota.xml",
            "https://thebogotapost.com/feed",
            "https://thecitypaperbogota.com/feed"
        ],
        "medellín": [
            "https://www.elcolombiano.com/rss",
            "https://www.minuto30.com/feed",
            "https://teleantioquia.co/noticias/feed"
        ],
        "cali": [
            "https://occidente.co/feed",
            "https://www.elpais.com.co/rss",
            "https://radiorelojcali.com/noticias/feed"
        ]
    }

    fuentes_ciudad = fuentes_por_ciudad.get(ciudad, [])
    return fuentes_ciudad + fuentes_generales

def mostrar_noticias(noticias):
    if noticias:
        for n in noticias[:5]:
            with st.expander(n["titulo"]):
                st.write(n["resumen"][:300] + "...")
                st.markdown(f"[Leer noticia completa]({n['link']})")
    else:
        st.info("Sin noticias de orden público al momento.")

def mostrar_estado_vias(ciudad=None):
    st.markdown("---")
    st.subheader("🚧 Estado de las vías en Colombia")
    try:
        df = pd.read_excel(resource_path("red_vial_invias_2025-07-24.xlsx"), engine="openpyxl")
        columnas_clave = ["sector", "tramo", "estado", "observacion_invias"]
        df_filtrado = df[columnas_clave].dropna(subset=["sector", "tramo", "estado"])

        if ciudad:
            ciudad_normalizada = unidecode.unidecode(str(ciudad).lower())
            df_filtrado = df_filtrado[df_filtrado.apply(
                lambda row: ciudad_normalizada in unidecode.unidecode(str(row.get("tramo","")).lower()) 
                            or ciudad_normalizada in unidecode.unidecode(str(row.get("sector","")).lower()),
                axis=1
            )]

        filtro = st.text_input("Filtrar por tramo o sector", "").strip()
        if filtro:
            filtro_normalizado = unidecode.unidecode(filtro.lower())
            df_filtrado = df_filtrado[df_filtrado.apply(
                lambda row: filtro_normalizado in unidecode.unidecode(str(row.get("tramo","")).lower()) 
                            or filtro_normalizado in unidecode.unidecode(str(row.get("sector","")).lower()),
                axis=1
            )]

        st.dataframe(df_filtrado, use_container_width=True)
        

    except Exception as e:
        st.error(f"Error al cargar el archivo de vías: {e}")



# ---------------- Main ----------------

def main():
    ciudad, consultar = mostrar_logo_sidebar()
    estilos_personalizados()

    if consultar:
        ciudad = str(ciudad or "").strip()
        if not ciudad:
            st.warning("Por favor ingrese una ciudad antes de consultar.")
            return

        st.markdown("---")
        st.subheader(f"🌤 Clima actual – {ciudad.title()}")
        key = st.secrets.get("WEATHER_API_KEY", "")
        obtener_clima(ciudad, key)

        st.markdown("---")
        st.subheader("📰 Noticias de orden público (filtradas por ciudad)")
        feeds = obtener_fuentes_por_ciudad(ciudad.lower())
        keywords = [
            "orden público", "seguridad", "homicidio", "hurto", "secuestro",
            "eln", "clan del golfo", "disidencias", "policía", "ejército"
        ]
        diccionario_municipios = cargar_diccionario_municipios()
        try:
            import feedparser
            with st.spinner("Cargando noticias…"):
                noticias = []
                ciudad_normalizada = unidecode.unidecode(ciudad.lower())
                departamento = diccionario_municipios.get(ciudad.title(), "")
                departamento_normalizada = unidecode.unidecode(departamento.lower()) if departamento else ""
                keywords_ciudad = keywords + [ciudad_normalizada]
                if departamento_normalizada:
                    keywords_ciudad.append(departamento_normalizada)
                seen = set()
                for url in feeds:
                    try:
                        feed = feedparser.parse(url)
                        for entry in feed.entries:
                            titulo = entry.title
                            link = entry.link
                            resumen = getattr(entry, "summary", "")
                            texto = unidecode.unidecode(f"{titulo} {resumen}".lower())
                            if any(k in texto for k in keywords_ciudad) and link not in seen:
                                seen.add(link)
                                noticias.append({"titulo": titulo, "resumen": resumen, "link": link})
                    except Exception:
                        continue
                if not noticias and departamento_normalizada:
                    for url in feeds:
                        try:
                            feed = feedparser.parse(url)
                            for entry in feed.entries:
                                titulo = entry.title
                                link = entry.link
                                resumen = getattr(entry, "summary", "")
                                texto = unidecode.unidecode(f"{titulo} {resumen}".lower())
                                if departamento_normalizada in texto and link not in seen:
                                    seen.add(link)
                                    noticias.append({"titulo": titulo, "resumen": resumen, "link": link})
                        except Exception:
                            continue
                mostrar_noticias(noticias)
        except ModuleNotFoundError:
            st.warning("El módulo 'feedparser' no está instalado. No se pueden mostrar noticias.")

        mostrar_estado_vias(ciudad)

        st.success("Actualizado: " + datetime.now().strftime("%d/%m %H:%M"))

       

with st.expander("📋 Ver Decálogo de Seguridad para Desplazamientos de Funcionarios"):
    try:
        image = Image.open("Decalogo.png")
        st.image(resource_path("Decalogo.png"), caption="Decálogo de Seguridad SMA",use_column_width=True)
    except FileNotFoundError:
        st.warning("No se encontró el archivo Decalogo.png en la carpeta del proyecto.")


# ---------------- Run ----------------

# REEMPLAZA EL BLOQUE ANTERIOR POR ESTE:
if __name__ == '__main__':
    # Esta condición revisa si el script se está ejecutando como un paquete congelado (un .exe de PyInstaller)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        from streamlit.web import cli
        # Reconfigura los argumentos para llamar al comando 'streamlit run' sobre sí mismo
        sys.argv = ["streamlit", "run", sys.executable, "--", *sys.argv[1:]]
        # Ejecuta el servidor de Streamlit
        cli.main()
    else:
        print("--- MODO DESARROLLO DETECTADO, CORRIENDO SCRIPT ---") # <-- AÑADE ESTA LÍNEA
        main()
        # Si no es un .exe, simplemente corre la función main como antes
        