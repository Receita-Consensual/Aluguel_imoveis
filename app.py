import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Lugar",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS "SUPER VIBRANT" & LIMPEZA TOTAL
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
    
    /* Fonte Moderna */
    html, body, [class*="css"] {font-family: 'Poppins', sans-serif;}
    
    /* --- 🚫 ZONA DE EXTERMÍNIO DE MENUS 🚫 --- */
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    header {display: none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    
    /* --- CORES E VIDA --- */
    
    /* Título com Gradiente (O efeito "Uau") */
    .brand-text {
        background: linear-gradient(45deg, #820AD1, #FF0080);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: -10px;
    }
    
    /* Subtítulo */
    .brand-sub {
        color: #555;
        font-size: 1.2rem;
        font-weight: 400;
        margin-bottom: 25px;
    }

    /* Botão Principal (Gradiente Vibrante) */
    .stButton>button {
        background: linear-gradient(90deg, #820AD1 0%, #E6007A 100%);
        color: white;
        border: none;
        border-radius: 12px;
        height: 3.5em;
        font-weight: 700;
        font-size: 16px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(230, 0, 122, 0.3);
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 6px 20px rgba(230, 0, 122, 0.5);
        color: white;
    }

    /* Inputs (Caixas de Texto Arredondadas) */
    .stTextInput>div>div>input {
        border-radius: 12px;
        border: 2px solid #eee;
        padding: 10px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #820AD1;
        box-shadow: 0 0 10px rgba(130, 10, 209, 0.1);
    }

    /* Card do Mapa (Estilo Airbnb Moderno) */
    .popup-card {
        width: 240px;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        background: white;
        font-family: 'Poppins', sans-serif;
    }
    .popup-img {
        width: 100%;
        height: 140px;
        object-fit: cover;
    }
    .popup-body {
        padding: 15px;
    }
    .popup-price {
        color: #820AD1;
        font-weight: 800;
        font-size: 20px;
    }
    .popup-badge {
        background: #E6007A;
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: bold;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 5px;
    }
    .popup-btn {
        display: block;
        background: black;
        color: white;
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 600;
        margin-top: 10px;
        transition: background 0.2s;
    }
    .popup-btn:hover { background: #333; }
    
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
        # Pega dados e garante que não tem lat 0
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(600).execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

# --- 3. SIDEBAR (Discreta) ---
with st.sidebar:
    st.markdown("### 🐞 Central Beta")
    with st.form("bug_report"):
        st.write("Viu algo estranho?")
        msg = st.text_area("Descreva aqui")
        if st.form_submit_button("Enviar Report") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": msg, "ativo": False, "plano": "beta_vibrant"}).execute()
            st.success("Recebido!")

# --- 4. HEADER (LOGO VIBRANTE) ---
c1, c2 = st.columns([1, 12])
with c2:
    st.markdown('<div class="brand-text">Lugar</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Encontre o seu canto em Portugal.</div>', unsafe_allow_html=True)

df_total = carregar_dados()

# --- 5. BUSCA (SEM TRAVAMENTOS) ---
# Usamos container para agrupar e dar destaque
with st.container():
    c_search, c_type, c_btn = st.columns([3, 1, 1])
    
    with c_search:
        # Ícone de lupa no placeholder
        local_input = st.text_input("Para onde vamos?", placeholder="🔍 Ex: Lefties Aveiro, Trindade Porto...")
    
    with c_type:
        st.write("") 
        tipos = st.multiselect("Filtro", ["T1", "T2", "T3", "Quarto"], default=["T1", "T2"], label_visibility="collapsed")

    with c_btn:
        st.write("") 
        # O botão agora tem aquele gradiente roxo/rosa definido no CSS
        buscar = st.button("Buscar Agora")

# --- 6. MAPA COLORIDO ---
map_center = [39.55, -7.85] 
zoom_start = 7
ponto_referencia = None

# Lógica GPS (Só roda no clique = Rápido)
if buscar and local_input:
    geolocator = Nominatim(user_agent="lugar_vibrant_v1")
    try:
        loc = geolocator.geocode(f"{local_input}, Portugal", timeout=10)
        if loc:
            map_center = [loc.latitude, loc.longitude]
            zoom_start = 15
            ponto_referencia = loc
        else:
            st.warning("Local não encontrado exato. Mostrando mapa geral.")
    except:
        st.error("Erro de conexão. Tente novamente.")

st.write("") 

# USANDO "OpenStreetMap" PARA CORES VIVAS (Verde é verde, mar é azul)
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)

# 1. SEU DESTINO (Pino Preto Grande)
if ponto_referencia:
    folium.Marker(
        [ponto_referencia.latitude, ponto_referencia.longitude],
        popup=f"<b>🎯 SEU DESTINO</b>",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(m)
    # Círculo Rosa Vibrante em volta
    folium.Circle([ponto_referencia.latitude, ponto_referencia.longitude], radius=1500, color="#E6007A", fill=True, fill_opacity=0.1).add_to(m)

# 2. IMÓVEIS (Pinos Coloridos)
marker_cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            
            # Popup "Estilo Airbnb"
            html = f"""
            <div class="popup-card">
                <img src="{img}" class="popup-img">
                <div class="popup-body">
                    <span class="popup-badge">Novo</span>
                    <div class="popup-price">{preco}</div>
                    <div class="popup-title">{row.get('titulo','')[:40]}...</div>
                    <a href="{row.get('link')}" target="_blank" class="popup-btn">Ver Detalhes</a>
                </div>
            </div>
            """
            
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html,
                # Ícones Roxos (Purple) combinam com a marca
                icon=folium.Icon(color="purple", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=650, returned_objects=[])

# --- 7. RODAPÉ (Capture Leads) ---
st.write("---")
st.markdown("<h3 style='text-align: center; color: #333;'>🚀 Entre para o Clube Beta</h3>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666;'>Garanta acesso vitalício gratuito antes que vire pago.</p>", unsafe_allow_html=True)

with st.form("lista_vip"):
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1: e = st.text_input("E-mail", placeholder="seu@email.com")
    with c2: c = st.text_input("Cidade", placeholder="Ex: Porto")
    with c3: 
        st.write("")
        st.write("")
        # Botão dentro do form herda o estilo vibrante
        btn = st.form_submit_button("Quero Entrar")
    
    if btn and e and supabase:
        supabase.table("alertas_clientes").insert({"user_id": e, "termo_busca": c, "ativo": True, "plano": "beta_vip"}).execute()
        st.balloons()