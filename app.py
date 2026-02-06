import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
import numpy as np

# --- 1. CONFIGURAÇÃO ULTRA-LEVE ---
st.set_page_config(page_title="Lugar", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding: 1rem !important;}
    .stApp { background: #f5f7fa; }
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.5rem; font-weight: 800; text-align: center; display: block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CREDENCIAIS ---
GOOGLE_API_KEY = "AIzaSyCws8dm1mPhPKdu4VUk7BTBEe25qGZDrb4"
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data(ttl=30)
def carregar_dados():
    try:
        # Pega os dados mas garante que não venha nada vazio que quebre o mapa
        res = supabase.table("imoveis").select("*").neq("lat", 0).limit(500).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            # Jitter (Tremor) para espalhar os pinos que o robô salvou na cidade
            df['lat'] += np.random.uniform(-0.0008, 0.0008, size=len(df))
            df['lon'] += np.random.uniform(-0.0008, 0.0008, size=len(df))
        return df
    except:
        return pd.DataFrame()

# --- 3. UI ---
st.markdown('<span class="brand-text">Lugar</span>', unsafe_allow_html=True)

df_total = carregar_dados()

c_main = st.container()
with c_main:
    col_search, col_btn = st.columns([8, 2])
    with col_search:
        local_input = st.text_input("Localização", placeholder="Ex: Figueira da Foz...", label_visibility="collapsed")
    with col_btn:
        buscar = st.button("🔍 Buscar")

# --- 4. MAPA ---
map_center = [39.55, -7.85]
zoom_start = 7

if buscar and local_input:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={local_input}&key={GOOGLE_API_KEY}"
    try:
        r = requests.get(url).json()
        if r['status'] == 'OK':
            loc = r['results'][0]['geometry']['location']
            map_center = [loc['lat'], loc['lng']]
            zoom_start = 14
            # Manda o robô se não houver nada
            cidade = local_input.split(",")[0].strip()
            supabase.table("demandas").insert({"termo": cidade, "status": "pendente"}).execute()
            st.toast(f"Buscando em {cidade}...")
    except: pass

# Google Maps Tiles
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
Fullscreen().add_to(m)
LocateControl(auto_start=False).add_to(m)

if not df_total.empty:
    cluster = MarkerCluster().add_to(m)
    for _, row in df_total.iterrows():
        try:
            p = f"€ {float(row['preco']):,.0f}" if row['preco'] else "Consultar"
            html = f"<b>{p}</b><br><a href='{row['link']}' target='_blank'>Ver Detalhes</a>"
            folium.Marker([row['lat'], row['lon']], popup=html, icon=folium.Icon(color="purple", icon="home")).add_to(cluster)
        except: continue

# O segredo para NÃO TRAVAR: returned_objects=[]
st_folium(m, width="100%", height=550, returned_objects=[])

# --- 5. RODAPÉ ---
if st.button("🔄 Atualizar Mapa"):
    st.cache_data.clear()
    st.rerun()