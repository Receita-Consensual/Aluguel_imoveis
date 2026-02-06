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

# Coordenadas de Segurança
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

# CSS Estilo Google
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Roboto', sans-serif;}
    #MainMenu, footer, header {visibility: hidden;}
    
    .map-card {
        background: white; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        width: 250px; overflow: hidden; font-family: 'Roboto', sans-serif;
    }
    .map-img {height: 140px; width: 100%; object-fit: cover;}
    .map-info {padding: 10px;}
    .map-price {font-size: 18px; font-weight: 700; color: #1a73e8;}
    .map-title {font-size: 14px; color: #202124; margin: 4px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
    .btn-maps {display: block; margin-top: 8px; text-align: center; background: #1a73e8; color: white; padding: 8px; border-radius: 4px; text-decoration: none; font-weight: 500;}
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

# --- 3. SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'

# --- 4. FUNÇÃO DE DADOS BLINDADA (CACHE) ---
# Aqui está a correção: TTL de 60s impede o pisca-pisca
@st.cache_data(ttl=60)
def carregar_dados_estaveis(preco_max, cidade_filtro):
    if not supabase: return pd.DataFrame()
    
    try:
        # Pega dados (Aumentado para 3000)
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(3000).execute()
        df_raw = pd.DataFrame(response.data)
        
        if df_raw.empty: return pd.DataFrame()
        
        # Filtros
        df = df_raw[df_raw['preco'] <= preco_max]
        if cidade_filtro != "Todas":
            df = df[df['endereco'].str.contains(cidade_filtro, case=False, na=False)]
            
        # Correção Lat/Lon (DENTRO DO CACHE = ESTABILIDADE)
        def corrigir_lat(row):
            if row['lat'] != 0: return row['lat']
            end = str(row['endereco']).lower()
            for c, coords in COORDS_FIXAS.items():
                if c in end: return coords[0] + random.uniform(-0.015, 0.015)
            return 39.5

        def corrigir_lon(row):
            if row['lon'] != 0: return row['lon']
            end = str(row['endereco']).lower()
            for c, coords in COORDS_FIXAS.items():
                if c in end: return coords[1] + random.uniform(-0.015, 0.015)
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
    
    # Login
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
    filtro_cidade = st.selectbox("📍 Filtrar Cidade", ["Todas"] + [k.capitalize() for k in sorted(COORDS_FIXAS.keys())])
    filtro_preco = st.slider("💰 Preço Máximo", 0, 5000, 2500)

# --- 6. EXECUÇÃO ---
# Chama a função cacheada
df = carregar_dados_estaveis(filtro_preco, filtro_cidade)

if not df.empty:
    st.sidebar.success(f"Carregados: {len(df)}")
else:
    st.sidebar.warning("Carregando...")

# --- 7. MAPA ---
# Centro do Mapa
if not df.empty and filtro_cidade != "Todas":
    center = [df['lat'].mean(), df['lon'].mean()]
    zoom = 13
elif not df.empty:
    center = [39.6, -8.0] # Visão Portugal
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
        if row['lat'] != 39.5: 
            img = row.get('imagem')
            if not img or str(img) == 'nan': img = "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=400&q=80"
            
            preco = f"€ {row['preco']:,.0f}" if row['preco'] > 0 else "Sob Consulta"
            
            html = f"""
            <div class="map-card">
                <a href="{row.get('link')}" target="_blank">
                    <img src="{img}" class="map-img">
                </a>
                <div class="map-info">
                    <div class="map-price">{preco}</div>
                    <div class="map-title">{row.get('titulo', 'Imóvel')}</div>
                    <div style="font-size:11px; color:#666;">📍 {row.get('endereco', '')}</div>
                    <a href="{row.get('link')}" target="_blank" class="btn-maps">Ver Anúncio</a>
                </div>
            </div>
            """
            
            folium.Marker(
                [row['lat'], row['lon']],
                popup=folium.Popup(html, max_width=260),
                icon=folium.Icon(color="blue", icon="home", prefix="fa")
            ).add_to(marker_cluster)

# returned_objects=[] é o segredo para o mapa não recarregar a pagina ao clicar
st_folium(m, width=None, height=700, returned_objects=[])