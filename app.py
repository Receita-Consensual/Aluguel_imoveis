import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import random

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chaves Supabase (Hardcoded para funcionar no copy-paste)
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

# Coordenadas Fixas de Cidades (Para corrigir imóveis sem GPS)
COORDS_FIXAS = {
    "aveiro": [40.6405, -8.6538],
    "porto": [41.1579, -8.6291],
    "lisboa": [38.7223, -9.1393],
    "braga": [41.5454, -8.4265],
    "coimbra": [40.2033, -8.4103],
    "faro": [37.0194, -7.9304],
    "leiria": [39.7495, -8.8077],
    "setúbal": [38.5244, -8.8882],
    "viseu": [40.6566, -7.9124],
    "viana": [41.6918, -8.8344],
    "figueira": [40.1517, -8.8569],
    "matosinhos": [41.1844, -8.6963],
    "gaia": [41.1333, -8.6167]
}

# CSS Estilo Google Maps
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Roboto', sans-serif;}
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Estilo do Card no Mapa */
    .map-card {
        background: white; 
        border-radius: 8px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        width: 220px !important;
        overflow: hidden; 
        font-family: 'Roboto', sans-serif;
        text-align: left;
    }
    
    /* Botão Ver Anúncio */
    .btn-maps {
        display: block; 
        margin-top: 10px; 
        text-align: center; 
        background: #1a73e8; 
        color: white !important; 
        padding: 8px; 
        border-radius: 4px; 
        text-decoration: none; 
        font-weight: 500;
        font-size: 13px;
    }
    .btn-maps:hover {background: #1558b0;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        return None

supabase = init_connection()

# --- 3. SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'

# --- 4. FUNÇÃO DE DADOS BLINDADA (CACHE 60s) ---
# O TTL 60 impede que o mapa fique piscando
@st.cache_data(ttl=60)
def carregar_dados_estaveis(preco_max, cidade_filtro):
    if not supabase: return pd.DataFrame()
    try:
        # Busca até 2000 imóveis
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(2000).execute()
        df_raw = pd.DataFrame(response.data)
        if df_raw.empty: return pd.DataFrame()
        
        # Filtros
        df = df_raw.copy()
        if 'preco' in df.columns:
            df = df[df['preco'] <= preco_max]
        
        if cidade_filtro != "Todas":
            df = df[df['endereco'].str.contains(cidade_filtro, case=False, na=False)]
            
        # Correção Lat/Lon com "Ruído" Fixo (dentro do cache)
        def corrigir_lat(row):
            if row['lat'] != 0: return row['lat']
            end = str(row['endereco']).lower()
            for c, coords in COORDS_FIXAS.items():
                if c in end: return coords[0] + random.uniform(-0.02, 0.02)
            return 39.5

        def corrigir_lon(row):
            if row['lon'] != 0: return row['lon']
            end = str(row['endereco']).lower()
            for c, coords in COORDS_FIXAS.items():
                if c in end: return coords[1] + random.uniform(-0.02, 0.02)
            return -8.0

        df['lat'] = df.apply(corrigir_lat, axis=1)
        df['lon'] = df.apply(corrigir_lon, axis=1)
        return df
    except:
        return pd.DataFrame()

# --- 5. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)
    st.markdown("### Receita Imob")
    
    if not st.session_state['logged_in']:
        with st.expander("🔐 Entrar"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                if supabase:
                    res = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
                    if res.data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_plan'] = res.data[0]['plano']
                        st.rerun()
                    else:
                        st.error("Erro")
    else:
        st.success("Logado como PRO")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.divider()
    opcoes_cidades = ["Todas"] + [k.capitalize() for k in sorted(COORDS_FIXAS.keys())]
    filtro_cidade = st.selectbox("📍 Filtrar Cidade", opcoes_cidades)
    filtro_preco = st.slider("💰 Preço Máximo", 0, 5000, 2500)

# --- 6. MAPA ---
df = carregar_dados_estaveis(filtro_preco, filtro_cidade)

# Foco do Mapa
if not df.empty and filtro_cidade != "Todas":
    center = [df['lat'].mean(), df['lon'].mean()]
    zoom = 13
elif not df.empty:
    center = [39.6, -8.0]
    zoom = 7
else:
    center = [39.6, -8.0]
    zoom = 7

m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap", control_scale=True)
LocateControl().add_to(m)
Fullscreen().add_to(m)

marker_cluster = MarkerCluster().add_to(m)

if not df.empty:
    for _, row in df.iterrows():
        # Só exibe se estiver em Portugal (lat diferente de 0 absoluto)
        if row['lat'] != 0: 
            img = row.get('imagem')
            if not img or str(img) == 'nan': 
                img = "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=400&q=80"
            
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            titulo_curto = str(row.get('titulo', 'Imóvel'))[:50]
            
            # HTML DO POPUP CORRIGIDO (FOTO COMO BACKGROUND)
            html = f"""
            <div class="map-card">
                <a href="{row.get('link')}" target="_blank" style="text-decoration:none;">
                    <div style="
                        width: 100%; 
                        height: 120px; 
                        background-image: url('{img}'); 
                        background-size: cover; 
                        background-position: center;
                    "></div>
                </a>
                <div class="map-info">
                    <div style="color: #1a73e8; font-weight: bold; font-size: 16px;">{preco}</div>
                    <div style="font-size: 13px; color: #333; margin: 5px 0; line-height: 1.2;">{titulo_curto}...</div>
                    <a href="{row.get('link')}" target="_blank" class="btn-maps">
                        Ver Anúncio
                    </a>
                </div>
            </div>
            """
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(html, max_width=240), # Fixa largura para não quebrar
                icon=folium.Icon(color="blue", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=700, returned_objects=[])