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

# --- CSS "AIRY" (LEVE E SEM CAIXAS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;700&display=swap');
    
    html, body, [class*="css"] {font-family: 'Poppins', sans-serif;}

    /* 1. FUNDO PLATINUM SUAVE */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        background-attachment: fixed;
    }
    
    /* 2. LIMPEZA TOTAL DE MENUS */
    #MainMenu, footer, header, div[data-testid="stToolbar"] {display: none !important;}
    .stDeployButton {display: none !important;}
    
    /* 3. TÍTULOS */
    .brand-container {
        text-align: center;
        padding: 30px 0 10px 0;
    }
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 4rem;
        font-weight: 800;
        letter-spacing: -2px;
    }
    .brand-badge {
        background-color: #2575fc;
        color: white;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.7rem;
        font-weight: bold;
        vertical-align: middle;
        margin-left: 10px;
        text-transform: uppercase;
    }
    .brand-sub {
        color: #555;
        font-size: 1.2rem;
        font-weight: 500;
        margin-top: -5px;
    }

    /* 4. REMOVI AS BORDAS DAS CAIXAS (VISUAL LIVRE) */
    div[data-testid="stVerticalBlock"] > div {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    /* 5. INPUTS E BOTÕES FLUTUANTES */
    .stTextInput>div>div>input {
        border-radius: 15px;
        border: none;
        padding: 15px;
        height: 3.5em;
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); /* Sombra suave para destacar do fundo */
    }
    
    .stButton>button {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        color: white;
        border: none;
        border-radius: 15px;
        height: 3.5em;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(37, 117, 252, 0.4);
        width: 100%;
        transition: transform 0.2s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        color: white;
    }

    /* 6. POPUPS DO MAPA */
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
    st.markdown("### Feedback Beta")
    with st.form("bug_report"):
        desc = st.text_area("Encontrou algum problema?")
        if st.form_submit_button("📢 Enviar") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": desc, "ativo": False, "plano": "beta_clean"}).execute()
            st.success("Recebido!")

# --- HEADER (TÍTULO SOLTO) ---
c1, c2, c3 = st.columns([1, 8, 1])
with c2:
    st.markdown("""
    <div class="brand-container">
        <span class="brand-text">Lugar</span><span class="brand-badge">BETA</span>
        <div class="brand-sub">O jeito mais rápido de encontrar casa em Portugal.</div>
    </div>
    """, unsafe_allow_html=True)

df_total = carregar_dados()

# --- BUSCA ALINHADA E LIMPA ---
st.write("") 
c_spacer_l, c_main, c_spacer_r = st.columns([1, 10, 1])

with c_main:
    # Removemos o st.container com borda. Agora é direto no fundo.
    c_search, c_type, c_btn = st.columns([5, 2, 2], vertical_alignment="bottom")
    
    with c_search:
        local_input = st.text_input("Busca Inteligente", placeholder="Ex: Lefties Aveiro, Hospital São João...", label_visibility="hidden")
    
    with c_type:
        tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1", "T2"], label_visibility="hidden")

    with c_btn:
        buscar = st.button("🔍 Buscar")

# --- MAPA ---
map_center = [39.55, -7.85] 
zoom_start = 7
ponto_referencia = None

if buscar and local_input:
    geolocator = Nominatim(user_agent="lugar_clean_v1")
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

# Mapa com sombra suave para destacar do fundo
st.markdown("<div style='box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-radius: 20px; overflow: hidden;'>", unsafe_allow_html=True)
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)

if ponto_referencia:
    folium.Marker([ponto_referencia.latitude, ponto_referencia.longitude], popup="<b>📍 SEU DESTINO</b>", icon=folium.Icon(color="black", icon="star", prefix="fa")).add_to(m)
    folium.Circle([ponto_referencia.latitude, ponto_referencia.longitude], radius=1500, color="#6a11cb", fill=True, fill_opacity=0.1).add_to(m)

marker_cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Consultar"
            html = f"""<div class="popup-card"><img src="{img}" class="popup-img"><div class="popup-body"><div class="popup-price">{preco}</div><div class="popup-title">{row.get('titulo','')[:45]}...</div><a href="{row.get('link')}" target="_blank" class="popup-btn">Ver Detalhes</a></div></div>"""
            folium.Marker([row['lat'], row['lon']], popup=html, icon=folium.Icon(color="purple", icon="home", prefix="fa")).add_to(marker_cluster)

st_folium(m, width=None, height=600, returned_objects=[])
st.markdown("</div>", unsafe_allow_html=True)

# --- LEAD MAGNET (CUPOM 20%) ---
st.write("---")

c_lead_L, c_lead_R = st.columns([1, 1])

with c_lead_L:
    st.markdown("### 🎟️ Cupom de Fundador (20% OFF)")
    st.write("Aproveite o Beta gratuito. Ao lançarmos a versão final paga, você terá **20% de desconto vitalício**.")
    st.info("Oferta exclusiva para quem se cadastrar hoje.")

with c_lead_R:
    with st.form("lista_vip_clean"):
        col_inp1, col_inp2 = st.columns(2)
        with col_inp1: email = st.text_input("Seu E-mail")
        with col_inp2: nome = st.text_input("Nome")
        
        btn_cupom = st.form_submit_button("Garanta Meu Desconto")
        
        if btn_cupom and email and supabase:
            # Salvamos com a tag 'founder_20_off' para filtrar depois
            supabase.table("alertas_clientes").insert({
                "user_id": email, 
                "termo_busca": "CUPOM_20_OFF", 
                "ativo": True, 
                "plano": "founder_20_off"
            }).execute()
            st.balloons()
            st.success("Cupom reservado! Avisaremos por e-mail no lançamento.")