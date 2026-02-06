import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
import numpy as np

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Lugar", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")

# CSS para esconder o lixo visual e acelerar o render
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}
    .stApp { background: #f5f7fa; }
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÕES ---
GOOGLE_API_KEY = "AIzaSyCws8dm1mPhPKdu4VUk7BTBEe25qGZDrb4"
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data(ttl=60) # Cache curto para ver os dados entrando em tempo real
def carregar_dados():
    try:
        # Pega apenas imóveis com lat/lon válidos
        res = supabase.table("imoveis").select("*").neq("lat", 0).limit(1000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            # Jitter para não empilhar
            df['lat'] += np.random.uniform(-0.0003, 0.0003, size=len(df))
            df['lon'] += np.random.uniform(-0.0003, 0.0003, size=len(df))
        return df
    except:
        return pd.DataFrame()

def buscar_google(query):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&key={GOOGLE_API_KEY}"
    try:
        r = requests.get(url).json()
        if r['status'] == 'OK':
            loc = r['results'][0]['geometry']['location']
            return loc['lat'], loc['lng'], r['results'][0]['formatted_address']
    except: pass
    return None

# --- 3. UI ---
st.markdown('<div style="text-align: center;"><span class="brand-text">Lugar</span></div>', unsafe_allow_html=True)

df_total = carregar_dados()

# Mostra contador de imóveis para você saber se o robô está funcionando
if not df_total.empty:
    st.caption(f"📍 {len(df_total)} imóveis disponíveis agora")
else:
    st.caption("📍 Aguardando o robô povoar o mapa...")

col_search, col_btn = st.columns([8, 2])
with col_search:
    local_input = st.text_input("Onde quer viver?", placeholder="Ex: Figueira da Foz, Aveiro...", label_visibility="collapsed")
with col_btn:
    buscar = st.button("🔍 Buscar")

# --- 4. LÓGICA DE BUSCA ---
map_center = [39.55, -7.85]
zoom_start = 7
ponto_ref = None

if buscar and local_input:
    res = buscar_google(local_input)
    if res:
        map_center = [res[0], res[1]]
        zoom_start = 14
        ponto_ref = res
        
        # Chama o robô se a cidade estiver vazia
        cidade = local_input.split(",")[0].strip()
        st.info(f"Buscando novos imóveis em {cidade}...")
        supabase.table("demandas").insert({"termo": cidade, "status": "pendente"}).execute()

# --- 5. MAPA OTIMIZADO ---
# Se o DF estiver vazio, desenha um mapa limpo rápido
google_tiles = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles=google_tiles, attr="Google")

if ponto_ref:
    folium.Marker([ponto_ref[0], ponto_ref[1]], icon=folium.Icon(color="black", icon="star")).add_to(m)

if not df_total.empty:
    cluster = MarkerCluster(disableClusteringAtZoom=16).add_to(m)
    for _, row in df_total.iterrows():
        # Popup simplificado para não travar
        html = f"<b>€ {row['preco']}</b><br><a href='{row['link']}' target='_blank'>Ver Detalhes</a>"
        folium.Marker([row['lat'], row['lon']], popup=html, icon=folium.Icon(color="purple", icon="home")).add_to(cluster)

# returned_objects=[] evita que o Streamlit recarregue o mapa toda hora (o que causa o travamento)
st_folium(m, width="100%", height=500, returned_objects=[])