import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import random

# CONFIGURAÇÃO
st.set_page_config(page_title="Receita Imob", page_icon="🏠", layout="wide", initial_sidebar_state="expanded")

SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

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

# COORDENADAS MANUAIS VIP (Para não depender do Google errar)
LOCAIS_MANUAIS = {
    "🏢 Altice Labs (Aveiro)": (40.3744, -8.3847), # Coordenada Exata Corrigida
    "🎓 Universidade de Aveiro": (40.6306, -8.6579),
    "🏥 Hospital de São João (Porto)": (41.1812, -8.6010)
}

LUGARES_VIP = [
    "📍 Digitar Outro Local Manualmente...",
    "🏢 Altice Labs (Aveiro)",
    "🎓 Universidade de Aveiro",
    "🏭 Bosch (Ovar)",
    "🏥 Hospital de São João (Porto)",
    "🛍️ Glicínias Plaza (Aveiro)",
    "✈️ Aeroporto do Porto"
]

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Roboto', sans-serif;}
    #MainMenu, footer, header {visibility: hidden;}
    .map-card {background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); width: 220px !important; overflow: hidden; font-family: 'Roboto', sans-serif; text-align: left;}
    .btn-maps {display: block; margin-top: 10px; text-align: center; background: #1a73e8; color: white !important; padding: 8px; border-radius: 4px; text-decoration: none; font-weight: 500; font-size: 13px;}
    .btn-maps:hover {background: #1558b0;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_connection():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None
supabase = init_connection()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'

# --- FUNÇÃO DE DADOS ---
@st.cache_data(ttl=60)
def carregar_dados_base():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(2000).execute()
        df_raw = pd.DataFrame(response.data)
        if df_raw.empty: return pd.DataFrame()

        # Aceita mais links
        def link_eh_bom(url):
            url = str(url).lower()
            return "/imovel/" in url or "/anuncio/" in url or ".htm" in url or "/venda/" in url or "/arrendamento/" in url
        
        df_raw = df_raw[df_raw['link'].apply(link_eh_bom)]
        
        # Correção Lat/Lon
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

        df_raw['lat'] = df_raw.apply(corrigir_lat, axis=1)
        df_raw['lon'] = df_raw.apply(corrigir_lon, axis=1)
        return df_raw
    except: return pd.DataFrame()

def geolocalizar(endereco):
    # Primeiro verifica se temos a coordenada manual (mais preciso)
    if endereco in LOCAIS_MANUAIS:
        return LOCAIS_MANUAIS[endereco], endereco

    try:
        clean = endereco.replace("📍 ", "").replace("🏢 ", "").replace("🏭 ", "").replace("🎓 ", "").replace("🏥 ", "")
        geolocator = Nominatim(user_agent="receita_imob_final")
        loc = geolocator.geocode(f"{clean}, Portugal")
        if loc: return (loc.latitude, loc.longitude), loc.address
        return None, None
    except: return None, None

# --- SIDEBAR & LOGIN ---
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
                    else: st.error("Erro")
    else:
        st.success("Logado como PRO")
        if st.button("Sair"):
            st.session_state['logged_in'] = False
            st.session_state['user_plan'] = 'free'
            st.rerun()
    
    st.divider()
    if st.session_state['user_plan'] == 'free':
        st.info("🔒 Vantagens PRO: Busca por Local de Trabalho & Raio.")
        opcoes_cidades = ["Todas"] + [k.capitalize() for k in sorted(COORDS_FIXAS.keys())]
        filtro_cidade = st.selectbox("📍 Cidade", opcoes_cidades)
    else:
        st.success("💎 Modo PRO Ativo")

# --- APP PRINCIPAL ---
df_base = carregar_dados_base()
ponto_central = None
termo_busca = None
raio_km = 3
filtro_preco = 2500

if st.session_state['user_plan'] == 'pro':
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            escolha = st.selectbox("🏢 Onde você trabalha?", options=LUGARES_VIP, index=None, placeholder="Escolha ou digite...")
            if escolha == "📍 Digitar Outro Local Manualmente...":
                termo_busca = st.text_input("Endereço:", placeholder="Rua do Ouro, Lisboa")
            elif escolha:
                termo_busca = escolha
        with c2: raio_km = st.slider("Raio (km)", 1, 15, 3)
        with c3: filtro_preco = st.slider("Max €", 0, 5000, 2000)
else:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1: st.text_input("🏢 Onde trabalha?", placeholder="🔒 Exclusivo PRO", disabled=True)
        with c2: filtro_preco = st.slider("Max €", 0, 5000, 2000)

df_final = pd.DataFrame()
if not df_base.empty:
    df_temp = df_base[df_base['preco'] <= filtro_preco]
    
    if st.session_state['user_plan'] == 'pro' and termo_busca:
        coords, end_encontrado = geolocalizar(termo_busca)
        if coords:
            ponto_central = coords
            st.success(f"📍 Centralizado em: **{termo_busca}**")
            
            def calc_dist(row):
                if row['lat'] == 39.5: return 9999
                return geodesic(coords, (row['lat'], row['lon'])).km
            
            df_temp['distancia'] = df_temp.apply(calc_dist, axis=1)
            df_final = df_temp[df_temp['distancia'] <= raio_km]
            if df_final.empty: st.warning(f"Nada encontrado a {raio_km}km.")
        else:
            st.error("Local não encontrado.")
            df_final = df_temp
    else:
        if st.session_state['user_plan'] == 'free' and 'filtro_cidade' in locals() and filtro_cidade != "Todas":
             df_final = df_temp[df_temp['endereco'].str.contains(filtro_cidade, case=False, na=False)]
        else:
             df_final = df_temp

# --- MAPA ---
if ponto_central:
    center = ponto_central
    zoom = 14
elif not df_final.empty:
    center = [df_final['lat'].mean(), df_final['lon'].mean()]
    zoom = 10 if st.session_state['user_plan'] == 'free' and filtro_cidade != "Todas" else 7
else:
    center = [39.6, -8.0]
    zoom = 7

m = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap", control_scale=True)
LocateControl().add_to(m)
Fullscreen().add_to(m)

if ponto_central:
    folium.Marker(ponto_central, popup=f"📍 {termo_busca}", icon=folium.Icon(color="black", icon="briefcase", prefix="fa")).add_to(m)
    folium.Circle(location=ponto_central, radius=raio_km * 1000, color="#3388ff", fill=True, fill_opacity=0.1).add_to(m)

marker_cluster = MarkerCluster().add_to(m)
if not df_final.empty:
    for _, row in df_final.iterrows():
        if row['lat'] != 39.5: 
            img = row.get('imagem')
            if not img or str(img) == 'nan': img = "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            titulo = str(row.get('titulo', 'Imóvel'))[:50]
            dist_tag = f"<span style='color:green; font-size:11px;'>🚶 {row['distancia']:.1f}km</span>" if 'distancia' in row else ""
            
            html = f"""
            <div class="map-card">
                <a href="{row.get('link')}" target="_blank" style="text-decoration:none;">
                    <div style="width: 100%; height: 120px; background-image: url('{img}'); background-size: cover; background-position: center;"></div>
                </a>
                <div style="padding:10px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color:#1a73e8; font-weight:bold;">{preco}</span>
                        {dist_tag}
                    </div>
                    <div style="font-size:13px; color:#333; margin:5px 0;">{titulo}...</div>
                    <a href="{row.get('link')}" target="_blank" class="btn-maps">Ver Anúncio</a>
                </div>
            </div>
            """
            folium.Marker([row['lat'], row['lon']], popup=folium.Popup(html, max_width=240), icon=folium.Icon(color="blue", icon="home", prefix="fa")).add_to(marker_cluster)

st_folium(m, width=None, height=700, returned_objects=[])