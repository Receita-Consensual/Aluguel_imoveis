import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL (BRANDING: LUGAR) ---
st.set_page_config(
    page_title="Lugar",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS "LIMPEZA TOTAL" (Esconde menus do Streamlit)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    /* Fonte Geral */
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    
    /* ESCONDER MENUS PADRÃO DO STREAMLIT (As setas vermelhas que você mandou) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;} /* Esconde o topo */
    .stDeployButton {display:none;} /* Esconde botão Manage App */
    
    /* CORES DA MARCA "LUGAR" (Roxo NuBank + Azul Tech) */
    .brand-title {
        color: #820AD1; /* Roxo estilo Nubank */
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 0;
        letter-spacing: -1px;
    }
    .brand-subtitle {
        color: #555;
        font-size: 1.1rem;
        margin-top: -10px;
        margin-bottom: 20px;
    }

    /* CARD DO IMÓVEL (Visual App) */
    .popup-card { width: 220px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); font-family: 'Inter', sans-serif; }
    .popup-img { width: 100%; height: 130px; object-fit: cover; }
    .popup-body { padding: 12px; background: white; }
    .popup-price { color: #820AD1; font-weight: 800; font-size: 18px; }
    .popup-title { font-size: 13px; font-weight: 600; color: #333; margin: 5px 0; }
    .popup-btn { 
        display: block; background: #000; color: white; text-align: center; 
        padding: 10px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 12px; margin-top: 10px;
    }
    .popup-btn:hover { background: #333; }
    
    /* BOTÃO DE BUSCA */
    .stButton>button {
        background-color: #820AD1; color: white; border-radius: 10px; height: 3em; font-weight: bold; border: none; width: 100%;
    }
    .stButton>button:hover { background-color: #6D08AF; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO & CACHE ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

@st.cache_data(ttl=300) 
def carregar_dados():
    if not supabase: return pd.DataFrame()
    try:
        # Limitamos a 600 e removemos Latitude 0
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(600).execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

# --- 3. SIDEBAR: BUGS ---
with st.sidebar:
    st.markdown("### 📍 Lugar (Beta)")
    st.write("Encontrou um erro?")
    with st.form("bug_report"):
        desc = st.text_area("Descreva o problema")
        if st.form_submit_button("Enviar Report") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": desc, "ativo": False, "plano": "beta"}).execute()
            st.success("Obrigado!")

# --- 4. HEADER (LIMPO E MODERNO) ---
c1, c2 = st.columns([1, 12])
with c2:
    st.markdown('<h1 class="brand-title">Lugar</h1>', unsafe_allow_html=True)
    st.markdown('<p class="brand-subtitle">Onde você quer viver hoje?</p>', unsafe_allow_html=True)

df_total = carregar_dados()

# --- 5. BUSCA RÁPIDA (Volta ao Input Simples para não travar) ---
with st.container(border=True):
    c_search, c_type, c_btn = st.columns([3, 1, 1])
    
    with c_search:
        local_input = st.text_input("Buscar endereço ou ponto de referência", placeholder="Ex: Lefties Aveiro, Hospital São João...")
    
    with c_type:
        st.write("") # Ajuste visual
        tipos = st.multiselect("Filtro", ["T1", "T2", "T3", "Quarto"], default=["T1", "T2"], label_visibility="collapsed", placeholder="Tipo")

    with c_btn:
        st.write("") 
        buscar = st.button("🔍 Buscar")

# --- 6. MAPA INTELIGENTE ---
map_center = [39.55, -7.85] 
zoom_start = 7
ponto_referencia = None

# Lógica de GPS (Só roda quando clica no botão -> NÃO TRAVA)
if buscar and local_input:
    geolocator = Nominatim(user_agent="lugar_app_beta")
    try:
        loc = geolocator.geocode(f"{local_input}, Portugal", timeout=10)
        if loc:
            map_center = [loc.latitude, loc.longitude]
            zoom_start = 15
            ponto_referencia = loc
            st.toast(f"📍 Localizado: {loc.address}")
        else:
            st.warning("Não encontramos esse local exato. Mostrando o mapa geral.")
    except:
        st.error("Erro de conexão. Tente novamente.")

st.write("") # Espaço

m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="CartoDB positron") # CartoDB é mais limpo/moderno que OSM
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)

# Pino do Local Pesquisado (Preto)
if ponto_referencia:
    folium.Marker(
        [ponto_referencia.latitude, ponto_referencia.longitude],
        popup=f"<b>📍 SEU DESTINO</b>",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(m)
    folium.Circle([ponto_referencia.latitude, ponto_referencia.longitude], radius=1500, color="#820AD1", fill=True, fill_opacity=0.05).add_to(m)

# Imóveis (Roxo da Marca)
marker_cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Consultar"
            
            html = f"""
            <div class="popup-card">
                <img src="{img}" class="popup-img">
                <div class="popup-body">
                    <div class="popup-price">{preco}</div>
                    <div class="popup-title">{row.get('titulo','')[:45]}...</div>
                    <a href="{row.get('link')}" target="_blank" class="popup-btn">Ver Detalhes</a>
                </div>
            </div>
            """
            # Ícone Roxo customizado
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="purple", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=600, returned_objects=[])

# --- 7. RODAPÉ LEAD ---
st.write("---")
st.markdown("<h3 style='text-align: center; color: #555;'>🚀 Seja um Membro Fundador</h3>", unsafe_allow_html=True)
with st.form("lista_espera"):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1: e = st.text_input("E-mail", placeholder="seu@email.com")
    with c2: c = st.text_input("Cidade", placeholder="Onde procura?")
    with c3: 
        st.write("")
        st.write("")
        btn = st.form_submit_button("Entrar na Lista")
    
    if btn and e and supabase:
        supabase.table("alertas_clientes").insert({"user_id": e, "termo_busca": c, "ativo": True, "plano": "lugar_beta"}).execute()
        st.balloons()