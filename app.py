import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import random

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Chaves
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

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

# BANCO DE DADOS DE LOCAIS ESTRATÉGICOS (PARA AUTOCOMPLETE FAKE)
LUGARES_VIP = [
    "📍 Digitar Outro Local Manualmente...",
    "🏢 Altice Labs (Aveiro)",
    "🏭 Bosch (Ovar)",
    "🏭 Bosch (Braga)",
    "🏭 Autoeuropa (Palmela)",
    "🎓 Universidade de Aveiro",
    "🎓 Universidade do Porto (Pólo Asprela)",
    "🎓 Universidade de Coimbra (Pólo I)",
    "🎓 Universidade do Minho (Gualtar)",
    "🎓 Instituto Superior Técnico (Lisboa)",
    "🏥 Hospital de São João (Porto)",
    "🏥 Hospital de Santo António (Porto)",
    "🏥 Hospital da Luz (Aveiro)",
    "🏥 Hospital de Santa Maria (Lisboa)",
    "🏥 CHUC (Hospitais da Universidade de Coimbra)",
    "🛍️ Glicínias Plaza (Aveiro)",
    "🛍️ Forum Aveiro",
    "🛍️ NorteShopping (Matosinhos)",
    "🛍️ Colombo (Lisboa)",
    "🛍️ Vasco da Gama (Lisboa)",
    "🛍️ Braga Parque",
    "✈️ Aeroporto do Porto (Sá Carneiro)",
    "✈️ Aeroporto de Lisboa (Humberto Delgado)",
    "✈️ Aeroporto de Faro",
    "🏙️ Torre dos Clérigos (Porto)",
    "🏙️ Marquês de Pombal (Lisboa)",
    "🏙️ Parque das Nações (Lisboa)",
    "🏙️ Avenida dos Aliados (Porto)",
    "💼 Farfetch (Matosinhos)",
    "💼 Critical Techworks (Porto)",
    "💼 Blip (Porto)",
    "💼 Feedzai (Lisboa)"
]

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Roboto', sans-serif;}
    #MainMenu, footer, header {visibility: hidden;}
    .map-card {background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); width: 220px !important; overflow: hidden; font-family: 'Roboto', sans-serif; text-align: left;}
    .btn-maps {display: block; margin-top: 10px; text-align: center; background: #1a73e8; color: white !important; padding: 8px; border-radius: 4px; text-decoration: none; font-weight: 500; font-size: 13px;}
    .btn-maps:hover {background: #1558b0;}
    
    /* Estilo para Dropdown */
    div[data-baseweb="select"] > div {
        border-radius: 12px;
        border-color: #dfe1e5;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None
supabase = init_connection()

# --- 3. SESSÃO ---
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'

# --- 4. FUNÇÃO DE DADOS ---
@st.cache_data(ttl=60)
def carregar_dados_base():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(2000).execute()
        df_raw = pd.DataFrame(response.data)
        if df_raw.empty: return pd.DataFrame()

        def link_eh_bom(url):
            url = str(url).lower()
            return "/imovel/" in url or "/anuncio/" in url or ".htm" in url
        
        df_raw = df_raw[df_raw['link'].apply(link_eh_bom)]
        
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
    try:
        # Remove emojis para buscar no Nominatim
        clean_address = endereco.replace("📍 ", "").replace("🏢 ", "").replace("🏭 ", "").replace("🎓 ", "").replace("🏥 ", "").replace("🛍️ ", "").replace("✈️ ", "").replace("🏙️ ", "").replace("💼 ", "")
        
        geolocator = Nominatim(user_agent="receita_imob_pro_v2")
        loc = geolocator.geocode(f"{clean_address}, Portugal")
        if loc: return (loc.latitude, loc.longitude), loc.address
        return None, None
    except: return None, None

# --- 5. INTERFACE & SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)
    st.markdown("### Receita Imob")
    
    if not st.session_state['logged_in']:
        with st.expander("🔐 Entrar (Membros)"):
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
        st.info("🔒 **Vantagens do PRO:**")
        st.markdown("- 🎯 **Busca Rápida** (Altice, Bosch, etc)")
        st.markdown("- 📏 **Raio Personalizado**")
        st.markdown("- ⚡ **Autocompletar Inteligente**")
        st.markdown("---")
        opcoes_cidades = ["Todas"] + [k.capitalize() for k in sorted(COORDS_FIXAS.keys())]
        filtro_cidade = st.selectbox("📍 Filtrar por Cidade", opcoes_cidades)
    else:
        st.success("💎 **Modo PRO Ativo**")

# CARREGA BASE
df_base = carregar_dados_base()

# --- ÁREA DE BUSCA ---
ponto_central = None
termo_busca = None
raio_km = 5
filtro_preco = 2500

if st.session_state['user_plan'] == 'pro':
    # --- INTERFACE PRO (AUTOCOMPLETE) ---
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1:
            # SELECTBOX COM PESQUISA (FUNCIONA COMO AUTOCOMPLETE)
            escolha_local = st.selectbox(
                "🏢 Onde você vai trabalhar/estudar?", 
                options=LUGARES_VIP,
                index=None, # Começa vazio
                placeholder="Digite para buscar (Ex: Altice, Bosch...)"
            )
            
            # Se escolher "Outro", abre caixa de texto
            if escolha_local == "📍 Digitar Outro Local Manualmente...":
                termo_busca = st.text_input("Digite o endereço exato:", placeholder="Rua do Ouro, Lisboa")
            elif escolha_local:
                termo_busca = escolha_local

        with c2:
            raio_km = st.slider("Raio (km)", 1, 15, 3)
        with c3:
            filtro_preco = st.slider("Max €", 0, 5000, 2000)
else:
    # --- INTERFACE FREE ---
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.text_input("🏢 Onde você trabalha?", placeholder="🔒 Exclusivo PRO (Ex: Altice, Hospital...)", disabled=True)
            st.caption("🔒 Faça upgrade para buscar por Pontos de Interesse.")
        with c2:
            filtro_preco = st.slider("Max €", 0, 5000, 2000)

# PROCESSAMENTO
df_final = pd.DataFrame()

if not df_base.empty:
    df_temp = df_base[df_base['preco'] <= filtro_preco]
    
    if st.session_state['user_plan'] == 'pro' and termo_busca:
        coords_busca, endereco_encontrado = geolocalizar(termo_busca)
        if coords_busca:
            ponto_central = coords_busca
            if "Outro" not in str(termo_busca):
                st.success(f"📍 Localizado: **{termo_busca}**")
            else:
                st.success(f"📍 Localizado: **{endereco_encontrado}**")
            
            def calcular_distancia(row):
                if row['lat'] == 39.5: return 9999
                return geodesic(coords_busca, (row['lat'], row['lon'])).km
            
            df_temp['distancia'] = df_temp.apply(calcular_distancia, axis=1)
            df_final = df_temp[df_temp['distancia'] <= raio_km]
            
            if df_final.empty: st.warning(f"Nada a {raio_km}km daqui. Aumente o raio!")
        else:
            st.error("Endereço não encontrado no mapa.")
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
            titulo_curto = str(row.get('titulo', 'Imóvel'))[:50]
            dist_tag = ""
            if 'distancia' in row: dist_tag = f"<span style='font-size:11px; color:green;'>🚶 {row['distancia']:.1f}km</span>"
            
            html = f"""
            <div class="map-card">
                <a href="{row.get('link')}" target="_blank" style="text-decoration:none;">
                    <div style="width: 100%; height: 120px; background-image: url('{img}'); background-size: cover; background-position: center;"></div>
                </a>
                <div class="map-info">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="color: #1a73e8; font-weight: bold; font-size: 16px;">{preco}</span>
                        {dist_tag}
                    </div>
                    <div style="font-size: 13px; color: #333; margin: 5px 0; line-height: 1.2;">{titulo_curto}...</div>
                    <a href="{row.get('link')}" target="_blank" class="btn-maps">Ver Anúncio</a>
                </div>
            </div>
            """
            folium.Marker([row['lat'], row['lon']], popup=folium.Popup(html, max_width=240), icon=folium.Icon(color="blue", icon="home", prefix="fa")).add_to(marker_cluster)

st_folium(m, width=None, height=700, returned_objects=[])