import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Lugar | Beta",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS DE "ALTA COSTURA" (DESIGN PREMIUM) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {font-family: 'Poppins', sans-serif;}

    /* --- 1. O FUNDO "PLATINUM BLUE" (COR SUAVE E MODERNA) --- */
    .stApp {
        background: linear-gradient(135deg, #E0EAFC 0%, #CFDEF3 100%);
        background-attachment: fixed;
    }
    
    /* --- 2. LIMPEZA TOTAL --- */
    #MainMenu, footer, header, div[data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    
    /* --- 3. LOGO E TÍTULO --- */
    .brand-container {
        text-align: center;
        padding: 10px 0;
        margin-bottom: 20px;
    }
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 800;
        letter-spacing: -2px;
    }
    .brand-badge {
        background-color: #2575fc;
        color: white;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        vertical-align: middle;
        margin-left: 10px;
        box-shadow: 0 4px 10px rgba(37, 117, 252, 0.3);
    }
    .brand-sub {
        color: #444;
        font-size: 1.1rem;
        font-weight: 500;
        margin-top: -10px;
    }

    /* --- 4. GLASSMORPHISM (CAIXAS DE VIDRO) --- */
    div[data-testid="stVerticalBlock"] > div {
        background: rgba(255, 255, 255, 0.75); /* Mais opaco para leitura */
        backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 15px;
        border: 1px solid rgba(255, 255, 255, 0.9);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
    }

    /* --- 5. BOTÕES E INPUTS --- */
    .stButton>button {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        color: white;
        border: none;
        border-radius: 12px;
        height: 3em; /* Altura ajustada para alinhar */
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(37, 117, 252, 0.4);
        width: 100%;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        color: white;
    }
    
    /* Inputs */
    .stTextInput>div>div>input {
        border-radius: 12px;
        border: 1px solid #ccc;
        padding: 10px;
        height: 3em; /* Mesma altura do botão */
    }

    /* --- 6. POPUPS DO MAPA --- */
    .popup-card {
        width: 220px; border-radius: 12px; overflow: hidden; 
        box-shadow: 0 5px 15px rgba(0,0,0,0.1); background: white;
    }
    .popup-img { width: 100%; height: 130px; object-fit: cover; }
    .popup-body { padding: 12px; }
    .popup-price { color: #6a11cb; font-weight: 800; font-size: 18px; }
    .popup-btn { 
        display: block; background: #222; color: white; text-align: center; 
        padding: 8px; border-radius: 8px; text-decoration: none; font-size: 12px; margin-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
@st.cache_resource
def init_connection():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

supabase = init_connection()

@st.cache_data(ttl=300) 
def carregar_dados():
    if not supabase: return pd.DataFrame()
    try:
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(600).execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

# --- SIDEBAR (FEEDBACK) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=50)
    st.markdown("### Ajude a Construir")
    with st.form("bug_report"):
        desc = st.text_area("Encontrou algum erro?")
        if st.form_submit_button("📢 Avisar a Equipe") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": desc, "ativo": False, "plano": "beta_glass"}).execute()
            st.success("Obrigado!")

# --- HEADER ---
c1, c2, c3 = st.columns([1, 8, 1])
with c2:
    st.markdown("""
    <div class="brand-container">
        <span class="brand-text">Lugar</span><span class="brand-badge">BETA ABERTO</span>
        <div class="brand-sub">O jeito mais rápido de encontrar casa em Portugal.</div>
    </div>
    """, unsafe_allow_html=True)

df_total = carregar_dados()

# --- BUSCA ALINHADA (O CORRETOR DE ALINHAMENTO) ---
st.write("") 
c_spacer_l, c_main, c_spacer_r = st.columns([1, 10, 1])

with c_main:
    with st.container():
        # vertical_alignment="bottom" É O SEGREDO PARA ALINHAR O BOTÃO COM A CAIXA
        c_search, c_type, c_btn = st.columns([5, 2, 2], vertical_alignment="bottom")
        
        with c_search:
            local_input = st.text_input("Onde você quer viver?", placeholder="Ex: Lefties Aveiro, Hospital São João...")
        
        with c_type:
            tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1", "T2"], label_visibility="hidden") # Hidden esconde o label "Tipo" para alinhar melhor

        with c_btn:
            buscar = st.button("🔍 Buscar Agora")

# --- MAPA INTELIGENTE ---
map_center = [39.55, -7.85] 
zoom_start = 7
ponto_referencia = None

if buscar and local_input:
    geolocator = Nominatim(user_agent="lugar_final_beta")
    try:
        loc = geolocator.geocode(f"{local_input}, Portugal", timeout=10)
        if loc:
            map_center = [loc.latitude, loc.longitude]
            zoom_start = 15
            ponto_referencia = loc
            st.toast(f"📍 Indo para: {loc.address}")
        else:
            st.warning("Local não encontrado. Mostrando visão geral.")
    except:
        st.error("Erro de conexão.")

st.write("")

# Mapa OpenStreetMap
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)

if ponto_referencia:
    folium.Marker(
        [ponto_referencia.latitude, ponto_referencia.longitude],
        popup=f"<b>📍 SEU DESTINO</b>",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(m)
    folium.Circle([ponto_referencia.latitude, ponto_referencia.longitude], radius=1500, color="#6a11cb", fill=True, fill_opacity=0.1).add_to(m)

marker_cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            
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
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="purple", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=600, returned_objects=[])

# --- LEAD MAGNET (CUPOM) ---
st.write("---")

c_lead_L, c_lead_R = st.columns([1, 1])

with c_lead_L:
    st.markdown("### 🎟️ Cupom de Fundador")
    st.write("Quem usa o Beta ganha **50% de desconto vitalício** no futuro.")
    st.info("Cadastre-se para garantir sua vaga.")

with c_lead_R:
    with st.form("lista_vip_glass"):
        col_inp1, col_inp2 = st.columns(2)
        with col_inp1: email = st.text_input("E-mail")
        with col_inp2: nome = st.text_input("Nome")
        
        btn_cupom = st.form_submit_button("Garanta Meu Desconto")
        
        if btn_cupom and email and supabase:
            supabase.table("alertas_clientes").insert({
                "user_id": email, 
                "termo_busca": "CUPOM_FUNDADOR", 
                "ativo": True, 
                "plano": "founder_coupon"
            }).execute()
            st.balloons()
            st.success("Cadastrado com sucesso!")