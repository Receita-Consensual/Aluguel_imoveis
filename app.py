import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
import numpy as np

# --- 1. CONFIGURAÇÃO DE SEO E PÁGINA ---
# Substitua pelo link que você copiou do Imgur ou GitHub
URL_DA_FOTO = "LINK_DA_FOTO_AQUI" 

st.set_page_config(
    page_title="Lugar | Imóveis no Mapa 🇵🇹",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Meta Tags para WhatsApp, Facebook e TikTok
st.markdown(
    f"""
    <head>
        <meta property="og:title" content="Lugar | Encontre sua casa no mapa 🤖">
        <meta property="og:description" content="O robô inteligente que varre a internet para encontrar seu próximo lar em Portugal e no Brasil.">
        <meta property="og:image" content="{URL_DA_FOTO}"> 
        <meta property="og:image:width" content="1200">
        <meta property="og:image:height" content="630">
        <meta property="og:url" content="https://aluguelimoveis-queo6rsnzidypueducznxq.streamlit.app/">
        <meta property="og:type" content="website">
    </head>
    """,
    unsafe_allow_html=True
)

# --- 2. CSS DE ALTA VISIBILIDADE (CORRIGIDO PARA MOBILE) ---
st.markdown("""
    <style>
    [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding: 1rem !important;}
    .stApp { background-color: #ffffff !important; }

    h1, h2, h3, p, span, label, [data-testid="stCaptionContainer"] {
        color: #1a1a1a !important;
        font-family: 'Inter', sans-serif;
    }

    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        color: #6a11cb;
        font-size: 2.8rem; font-weight: 800; text-align: center; display: block;
    }

    .stForm {
        background-color: #f8f9fa !important;
        border: 1px solid #e0e0e0 !important;
        padding: 20px !important;
        border-radius: 15px !important;
    }

    .stTextInput input {
        color: #1a1a1a !important;
        background-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONEXÕES ---
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
            df['lat'] += np.random.uniform(-0.0005, 0.0005, size=len(df))
            df['lon'] += np.random.uniform(-0.0005, 0.0005, size=len(df))
        return df
    except: return pd.DataFrame()

# --- 4. INTERFACE ---
st.markdown('<span class="brand-text">Lugar</span>', unsafe_allow_html=True)
df_total = carregar_dados()

if not df_total.empty:
    st.caption(f"📍 {len(df_total)} imóveis disponíveis agora")
else:
    st.caption("📍 O robô está a trabalhar... tente pesquisar uma cidade!")

col_search, col_btn = st.columns([8, 2])
with col_search:
    local_input = st.text_input("Onde quer viver?", placeholder="Ex: Aveiro, Porto...", label_visibility="collapsed")
with col_btn:
    buscar = st.button("🔍 Buscar")

# --- 5. LÓGICA DE BUSCA E LOGS ---
map_center = [39.55, -7.85]
zoom_start = 7

if buscar and local_input:
    try: supabase.table("logs_pesquisas").insert({"termo_buscado": local_input}).execute()
    except: pass

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={local_input}&key={GOOGLE_API_KEY}"
    r = requests.get(url).json()
    if r['status'] == 'OK':
        loc = r['results'][0]['geometry']['location']
        map_center = [loc['lat'], loc['lng']]
        zoom_start = 14
        cidade = local_input.split(",")[0].strip()
        supabase.table("demandas").insert({"termo": cidade, "status": "pendente"}).execute()

# --- 6. MAPA ---
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")
Fullscreen().add_to(m)
LocateControl(auto_start=False).add_to(m)

if not df_total.empty:
    cluster = MarkerCluster().add_to(m)
    for _, row in df_total.iterrows():
        try:
            p = f"€ {float(row['preco']):,.0f}" if row['preco'] else "Ver"
            html = f"<b>{p}</b><br><a href='{row['link']}' target='_blank'>Ver Detalhes</a>"
            folium.Marker([row['lat'], row['lon']], popup=html, icon=folium.Icon(color="purple", icon="home")).add_to(cluster)
        except: continue

mapa_data = st_folium(m, width="100%", height=500, returned_objects=["last_object_clicked"])

# --- 7. LOGS DE CLIQUES ---
if mapa_data.get("last_object_clicked"):
    click_lat = mapa_data["last_object_clicked"]["lat"]
    click_lon = mapa_data["last_object_clicked"]["lng"]
    match = df_total[(np.isclose(df_total['lat'], click_lat, atol=1e-4)) & (np.isclose(df_total['lon'], click_lon, atol=1e-4))]
    if not match.empty:
        try:
            supabase.table("logs_cliques").insert({"imovel_id": int(match.iloc[0]['id']), "titulo_imovel": match.iloc[0]['titulo']}).execute()
        except: pass

# --- 8. CUPOM DE FUNDADOR ---
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