import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import random # Para espalhar os pinos e não ficarem amontoados

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Coordenadas de "Resgate" (Se o robô não pegou lat/lon, usamos estas)
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
    "figueira": [40.1517, -8.8569]
}

# CSS (Estilo Google Maps Clean)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Roboto', sans-serif;}
    #MainMenu, footer, header {visibility: hidden;}
    
    .stApp {background-color: #ffffff;}
    
    /* Card do Mapa (Estilo Google) */
    .map-card {
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        width: 250px;
        overflow: hidden;
        font-family: 'Roboto', sans-serif;
    }
    .map-img {
        height: 140px;
        width: 100%;
        object-fit: cover;
    }
    .map-info {
        padding: 10px;
    }
    .map-price {
        font-size: 18px;
        font-weight: 700;
        color: #1a73e8; /* Azul Google */
    }
    .map-title {
        font-size: 14px;
        color: #202124;
        margin: 4px 0;
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis;
    }
    .btn-maps {
        display: block;
        margin-top: 8px;
        text-align: center;
        background: #1a73e8;
        color: white;
        padding: 8px;
        border-radius: 4px;
        text-decoration: none;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# --- 3. SESSÃO & LOGIN (Simplificado) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state:
    st.session_state['user_plan'] = 'free'

# --- 4. BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)
    st.markdown("### Receita Imob")
    
    # Login Rápido
    if not st.session_state['logged_in']:
        with st.expander("🔐 Entrar (Membros)"):
            email = st.text_input("Email")
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                # Validação Fake Rápida para Teste (Ou conecta no banco)
                if supabase:
                    res = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
                    if res.data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_plan'] = res.data[0]['plano']
                        st.rerun()
                    else:
                        st.error("Dados incorretos")
    else:
        st.success("Logado como PRO")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.rerun()

    st.divider()
    
    # FILTROS
    filtro_cidade = st.selectbox("📍 Cidade", ["Todas", "Aveiro", "Porto", "Lisboa", "Braga", "Coimbra", "Faro"])
    filtro_preco = st.slider("💰 Preço Máximo", 300, 5000, 2000)

# --- 5. LOGICA DE DADOS (CORREÇÃO DE COORDENADAS) ---
df = pd.DataFrame()

if supabase:
    try:
        # Pega TUDO (1000 imóveis)
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(1000).execute()
        df_raw = pd.DataFrame(response.data)
        
        if not df_raw.empty:
            # --- CORREÇÃO DE COORDENADAS (LAT 0 vira LAT DA CIDADE) ---
            def corrigir_lat(row):
                if row['lat'] != 0: return row['lat']
                # Se for 0, tenta achar a cidade no endereço
                end = str(row['endereco']).lower()
                for cidade, coords in COORDS_FIXAS.items():
                    if cidade in end:
                        # Adiciona um "ruído" aleatório para não ficarem empilhados
                        return coords[0] + random.uniform(-0.02, 0.02) 
                return 39.5 # Centro Portugal (Fallback)

            def corrigir_lon(row):
                if row['lon'] != 0: return row['lon']
                end = str(row['endereco']).lower()
                for cidade, coords in COORDS_FIXAS.items():
                    if cidade in end:
                        return coords[1] + random.uniform(-0.02, 0.02)
                return -8.0

            df_raw['lat'] = df_raw.apply(corrigir_lat, axis=1)
            df_raw['lon'] = df_raw.apply(corrigir_lon, axis=1)
            
            # Aplica Filtros
            df = df_raw[df_raw['preco'] <= filtro_preco]
            if filtro_cidade != "Todas":
                # Filtro simples de string
                df = df[df['endereco'].str.contains(filtro_cidade, case=False, na=False)]
                
    except Exception as e:
        st.error(f"Erro: {e}")

# --- 6. MAPA ESTILO GOOGLE ---
# Se não tiver dados filtrados, mostra Portugal inteiro
center = [39.6, -8.0]
zoom = 7

if not df.empty:
    center = [df['lat'].mean(), df['lon'].mean()]
    zoom = 10 if filtro_cidade == "Todas" else 13

# CRIAÇÃO DO MAPA (TILES OPENSTREETMAP = Colorido e Detalhado)
m = folium.Map(
    location=center, 
    zoom_start=zoom,
    tiles="OpenStreetMap", # MUDANÇA AQUI: Mapa colorido com ruas
    control_scale=True
)

LocateControl().add_to(m) # Botão de GPS
Fullscreen().add_to(m)    # Botão Tela Cheia

marker_cluster = MarkerCluster().add_to(m)

for _, row in df.iterrows():
    # Garante que temos foto
    img = row.get('imagem')
    if not img or str(img) == 'nan' or str(img) == 'None':
        img = "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=400&q=80"
    
    preco = f"€ {row['preco']:,.0f}" if row['preco'] > 0 else "Sob Consulta"
    
    # HTML DO POPUP (Estilo Card Google Maps)
    html = f"""
    <div class="map-card">
        <img src="{img}" class="map-img">
        <div class="map-info">
            <div class="map-price">{preco}</div>
            <div class="map-title">{row.get('titulo', 'Imóvel')}</div>
            <div style="font-size:11px; color:#666;">📍 {row.get('endereco', '')}</div>
            <a href="{row.get('link')}" target="_blank" class="btn-maps">
                Ver Anúncio ↗
            </a>
        </div>
    </div>
    """
    
    folium.Marker(
        [row['lat'], row['lon']],
        popup=folium.Popup(html, max_width=260),
        icon=folium.Icon(color="blue", icon="home", prefix="fa")
    ).add_to(marker_cluster)

# Renderiza ocupando tudo (sem margens feias)
st_folium(m, width=None, height=700)

# Contador flutuante
st.info(f"Mostrando {len(df)} oportunidades em tempo real.")