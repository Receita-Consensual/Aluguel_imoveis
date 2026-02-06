import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, LocateControl, Geocoder
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- 1. CONFIGURAÇÃO VISUAL (ESTILO APP) ---
st.set_page_config(
    page_title="Receita Imob App",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS PROFISSIONAL (Remove bordas, estiliza botões)
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button {
        background-color: #2e86de;
        color: white;
        border-radius: 20px;
        border: none;
        height: 3em;
        font-weight: bold;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }
    .stTextInput>div>div>input {
        border-radius: 20px;
    }
    /* Card flutuante de métrica */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #2e86de;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO BACKEND ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# --- 3. LÓGICA DE GEOLOCALIZAÇÃO (O "GOOGLE" GRATUITO) ---
def encontrar_coordenadas(endereco):
    geolocator = Nominatim(user_agent="receita_imob_app")
    try:
        # Força busca em Portugal para evitar erros
        loc = geolocator.geocode(f"{endereco}, Portugal")
        if loc:
            return loc.latitude, loc.longitude
        return None, None
    except:
        return None, None

# --- 4. INTERFACE PRINCIPAL ---

# Título flutuante
col_logo, col_search = st.columns([1, 6])
with col_logo:
    st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=60)
with col_search:
    st.markdown("### 🇵🇹 Receita Imob | Portugal")

# BARRA DE BUSCA INTELIGENTE (TIPO AIRBNB/GOOGLE)
with st.container(border=True):
    col_input, col_raio, col_btn = st.columns([4, 2, 1])
    
    with col_input:
        busca_local = st.text_input("📍 Onde você vai trabalhar/estudar?", placeholder="Ex: Hospital de Aveiro, Torre dos Clérigos, Shopping Vasco da Gama")
    
    with col_raio:
        raio_km = st.slider("Raio de busca (km)", 1, 20, 3)
    
    with col_btn:
        st.write("") # Espaçamento
        buscar = st.button("🔍 Buscar")

# --- 5. PROCESSAMENTO DO MAPA ---

# Valores padrão (Centro de Portugal)
map_center = [39.55, -7.84] 
zoom_level = 6
imoveis_filtrados = pd.DataFrame()

# Carrega TODOS os imóveis do banco (Cache para ser rápido)
if supabase:
    try:
        # Pega até 1000 imóveis para cobrir o país todo
        response = supabase.table("imoveis").select("*").limit(1000).execute()
        df_imoveis = pd.DataFrame(response.data)
    except:
        df_imoveis = pd.DataFrame()

# Lógica da Busca
ponto_referencia = None

if buscar and busca_local:
    lat_busca, lon_busca = encontrar_coordenadas(busca_local)
    
    if lat_busca:
        map_center = [lat_busca, lon_busca]
        zoom_level = 14 # Zoom bem perto
        ponto_referencia = (lat_busca, lon_busca)
        st.success(f"Mostrando imóveis a {raio_km}km de: **{busca_local}**")
    else:
        st.error("Local não encontrado em Portugal. Tente ser mais específico.")

# Filtro de Distância (Matemática Espacial)
if not df_imoveis.empty and ponto_referencia:
    # Calcula distância de cada imóvel para o ponto de busca
    # Nota: Precisamos converter lat/lon para float
    df_imoveis['lat'] = df_imoveis['lat'].astype(float)
    df_imoveis['lon'] = df_imoveis['lon'].astype(float)
    
    def calc_dist(row):
        if row['lat'] == 0: return 9999 # Ignora imóveis sem coord
        return geodesic(ponto_referencia, (row['lat'], row['lon'])).km

    df_imoveis['distancia'] = df_imoveis.apply(calc_dist, axis=1)
    
    # Filtra só os pertos
    imoveis_filtrados = df_imoveis[df_imoveis['distancia'] <= raio_km]
else:
    imoveis_filtrados = df_imoveis # Se não buscou, mostra tudo

# --- 6. RENDERIZAÇÃO DO MAPA ---

m = folium.Map(location=map_center, zoom_start=zoom_level, tiles="CartoDB positron")

# Adiciona o Ponto de Referência (Trabalho/Escola)
if ponto_referencia:
    folium.Marker(
        ponto_referencia,
        popup=f"📍 {busca_local}",
        icon=folium.Icon(color="black", icon="briefcase", prefix="fa")
    ).add_to(m)
    
    # Desenha o círculo do raio
    folium.Circle(
        location=ponto_referencia,
        radius=raio_km * 1000, # Metros
        color="#2e86de",
        fill=True,
        fill_opacity=0.1
    ).add_to(m)

# Agrupamento de Imóveis
marker_cluster = MarkerCluster().add_to(m)

if not imoveis_filtrados.empty:
    for _, row in imoveis_filtrados.iterrows():
        lat, lon = row.get('lat'), row.get('lon')
        if lat and lon and lat != 0:
            
            # Foto
            img_html = f"<img src='{row['imagem']}' width='100%' style='border-radius:8px; margin-bottom:8px;'>" if row.get('imagem') else ""
            preco = f"€ {row.get('preco')}" if row.get('preco') > 0 else "Consultar"
            
            # Popup Estilo Card
            html = f"""
            <div style='width: 240px; font-family: "Helvetica Neue", Arial, sans-serif; overflow: hidden;'>
                {img_html}
                <div style='padding: 5px;'>
                    <h4 style='margin:0; color:#2c3e50; font-size: 16px;'>{row.get('titulo', 'Imóvel')}</h4>
                    <p style='margin:4px 0; color:#27ae60; font-weight:bold; font-size: 14px;'>{preco}</p>
                    <p style='margin:4px 0; font-size:12px; color:#7f8c8d;'>📍 {row.get('endereco', '')}</p>
                    <a href='{row.get('link', '#')}' target='_blank' style='display:block; background-color:#ff4b4b; color:white; text-align:center; padding:10px; text-decoration:none; border-radius:20px; font-size:12px; font-weight:bold; margin-top:10px;'>Ver Imóvel</a>
                </div>
            </div>
            """
            
            folium.Marker(
                [lat, lon],
                popup=html,
                icon=folium.Icon(color="red", icon="home")
            ).add_to(marker_cluster)

# Botão de Geolocalização do Usuário (Mobile)
LocateControl().add_to(m)

# Exibe o mapa ocupando a largura total
st_folium(m, width=None, height=700)

# --- RODAPÉ INTELIGENTE ---
if imoveis_filtrados.empty and busca_local:
    st.warning("⚠️ Não encontramos imóveis nesta área ainda.")
    with st.expander("🔔 Quero ser avisado quando aparecer algo aqui!"):
        with st.form("alert_missing"):
            email_aviso = st.text_input("Seu E-mail")
            st.write(f"Criar alerta para: **{busca_local}** (+{raio_km}km)")
            submit_aviso = st.form_submit_button("Criar Alerta Automático")
            
            if submit_aviso and email_aviso and supabase:
                supabase.table("alertas_clientes").insert({
                    "user_id": email_aviso,
                    "termo_busca": f"Imóveis perto de {busca_local}",
                    "ativo": True,
                    "plano": "map_request"
                }).execute()
                st.success("Feito! Nosso robô vai começar a monitorar essa área agora.")