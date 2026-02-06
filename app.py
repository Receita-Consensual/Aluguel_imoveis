import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
import numpy as np

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Lugar", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")

# CSS para esconder lixo visual e estilizar a marca
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding: 1rem !important;}
    .stApp { background: #f5f7fa; }
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 3rem; font-weight: 800; text-align: center; display: block;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CREDENCIAIS ---
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
        res = supabase.table("imoveis").select("*").neq("lat", 0).limit(1000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            # Jitter para dispersar os pinos amontoados das fotos image_d3db80.jpg e image_d3dfc3.jpg
            df['lat'] += np.random.uniform(-0.0005, 0.0005, size=len(df))
            df['lon'] += np.random.uniform(-0.0005, 0.0005, size=len(df))
        return df
    except:
        return pd.DataFrame()

# --- INTERFACE ---
st.markdown('<span class="brand-text">Lugar</span>', unsafe_allow_html=True)
df_total = carregar_dados()

if not df_total.empty:
    st.caption(f"📍 {len(df_total)} imóveis disponíveis")
else:
    st.caption("📍 O robô está a povoar o mapa... tente pesquisar uma cidade!")

col_search, col_btn = st.columns([8, 2])
with col_search:
    local_input = st.text_input("Onde quer viver?", placeholder="Ex: Aveiro, Porto...", label_visibility="collapsed")
with col_btn:
    buscar = st.button("🔍 Buscar")

# --- LÓGICA ---
map_center = [39.55, -7.85]
zoom_start = 7

if buscar and local_input:
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={local_input}&key={GOOGLE_API_KEY}"
    r = requests.get(url).json()
    if r['status'] == 'OK':
        loc = r['results'][0]['geometry']['location']
        map_center = [loc['lat'], loc['lng']]
        zoom_start = 14
        cidade = local_input.split(",")[0].strip()
        supabase.table("demandas").insert({"termo": cidade, "status": "pendente"}).execute()

# MAPA GOOGLE
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
Fullscreen().add_to(m)
LocateControl(auto_start=False).add_to(m)

if not df_total.empty:
    cluster = MarkerCluster().add_to(m)
    for _, row in df_total.iterrows():
        try:
            p = f"€ {float(row['preco']):,.0f}" if row['preco'] else "Ver"
            html = f"<b>{p}</b><br><a href='{row['link']}' target='_blank'>Detalhes</a>"
            folium.Marker([row['lat'], row['lon']], popup=html, icon=folium.Icon(color="purple", icon="home")).add_to(cluster)
        except: continue

st_folium(m, width="100%", height=500, returned_objects=[])

# --- SEÇÃO DE CUPOM (RECUPERADA) ---
st.write("---")
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🎟️ Cupom de Fundador (20% OFF)")
    st.write("Garanta o seu desconto vitalício para quando o Lugar for lançado oficialmente.")
with c2:
    with st.form("vip_final"):
        email = st.text_input("Seu E-mail")
        if st.form_submit_button("Garantir Desconto") and email:
            supabase.table("alertas_clientes").insert({"user_id": email, "termo_busca": "FOUNDER", "ativo": True}).execute()
            st.balloons()
            st.success("Registado com sucesso!")