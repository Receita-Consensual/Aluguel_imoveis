import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import random

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed" # Barra fechada para dar foco no mapa
)

# Coordenadas Fixas de Resgate
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

# CSS Google Maps Style
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Roboto', sans-serif;}
    #MainMenu, footer, header {visibility: hidden;}
    .stApp {background-color: white;}
    
    /* Card do Mapa */
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

# --- 2. CONEXÃO E DADOS (COM CACHE ANTI-PISCA) ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# AQUI ESTÁ A CORREÇÃO: Cache Data (TTL 60s)
# Isso impede que o Python recalcule o Random a cada segundo
@st.cache_data(ttl=60)
def carregar_dados_blindados():
    if not supabase: return pd.DataFrame()
    
    try:
        # Pega dados
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(1000).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty: return df

        # --- CORREÇÃO DE COORDENADAS ---
        # Fazemos isso DENTRO do cache, então o "random" fica fixo por 60 segundos
        def corrigir_lat(row):
            if row['lat'] != 0: return row['lat']
            end = str(row['endereco']).lower()
            for cidade, coords in COORDS_FIXAS.items():
                if cidade in end:
                    return coords[0] + random.uniform(-0.03, 0.03) 
            return 39.5 # Fallback

        def corrigir_lon(row):
            if row['lon'] != 0: return row['lon']
            end = str(row['endereco']).lower()
            for cidade, coords in COORDS_FIXAS.items():
                if cidade in end:
                    return coords[1] + random.uniform(-0.03, 0.03)
            return -8.0

        df['lat'] = df.apply(corrigir_lat, axis=1)
        df['lon'] = df.apply(corrigir_lon, axis=1)
        
        return df
        
    except Exception as e:
        return pd.DataFrame()

# Carrega os dados (Agora eles são estáveis!)
df_estavel = carregar_dados_blindados()

# --- 3. BARRA LATERAL SIMPLIFICADA ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)
    st.markdown("### Receita Imob")
    
    cidades_unicas = ["Todas"]
    if not df_estavel.empty:
        # Tenta extrair cidades reais dos dados
        zonas_detectadas = [c for c in COORDS_FIXAS.keys() if df_estavel['endereco'].str.contains(c, case=False).any()]
        cidades_unicas += [z.capitalize() for z in zonas_detectadas]
        
    filtro_cidade = st.selectbox("📍 Filtrar Cidade", cidades_unicas)
    
    st.divider()
    st.info("💎 Membro PRO: Ativo")

# --- 4. MAPA ESTÁVEL ---

# Filtragem
df_mapa = df_estavel.copy()
center = [39.6, -8.0]
zoom = 7

if not df_mapa.empty:
    if filtro_cidade != "Todas":
        df_mapa = df_mapa[df_mapa['endereco'].str.contains(filtro_cidade, case=False, na=False)]
        if not df_mapa.empty:
            center = [df_mapa['lat'].mean(), df_mapa['lon'].mean()]
            zoom = 12

    # Renderiza o mapa
    m = folium.Map(
        location=center, 
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True
    )
    
    Fullscreen().add_to(m)
    
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df_mapa.iterrows():
        # Tratamento de Imagem
        img = row.get('imagem')
        if not img or str(img) == 'nan' or str(img) == 'None':
            img = "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=400&q=80"
        
        preco = f"€ {row['preco']:,.0f}" if row['preco'] > 0 else "Sob Consulta"
        
        html = f"""
        <div class="map-card">
            <img src="{img}" class="map-img">
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

    # Renderiza sem piscar (use_container_width=True ajuda na estabilidade)
    st_folium(m, width=None, height=700, returned_objects=[])

# Rodapé discreto
if not df_mapa.empty:
    st.caption(f"{len(df_mapa)} imóveis carregados.")