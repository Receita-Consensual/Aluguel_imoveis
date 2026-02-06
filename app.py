import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob (BETA)",
    page_icon="🚧",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .popup-card { width: 220px; font-family: sans-serif; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .popup-img { width: 100%; height: 120px; object-fit: cover; }
    .popup-body { padding: 10px; background: white; }
    .popup-price { color: #27ae60; font-weight: 800; font-size: 15px; }
    .popup-title { font-size: 13px; font-weight: 600; color: #333; margin: 5px 0; line-height: 1.2; }
    .popup-btn { 
        display: block; background: #2e86de; color: white; text-align: center; 
        padding: 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 12px; margin-top: 8px;
    }
    
    .feedback-box {
        background-color: #f1f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4757; margin-bottom: 20px;
    }
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
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(800).execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

# --- 3. SIDEBAR: BUGS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=50)
    st.title("Central Beta 🚧")
    with st.form("bug_report"):
        nome_bug = st.text_input("Seu Nome")
        desc_bug = st.text_area("O que aconteceu?")
        if st.form_submit_button("🐛 Reportar") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": desc_bug, "ativo": False, "plano": nome_bug}).execute()
            st.success("Enviado!")

# --- 4. HEADER ---
c1, c2 = st.columns([1, 10])
with c2:
    st.title("Receita Imob | Versão Beta")
    st.markdown("""
    <div class="feedback-box">
        🎯 <b>Nova Função:</b> Pesquise por lojas ou pontos exatos (ex: "Lefties Aveiro", "Hospital São João") para ver casas perto deles.
    </div>
    """, unsafe_allow_html=True)

df_total = carregar_dados()

# --- 5. BUSCA INTELIGENTE ---
with st.container(border=True):
    c_search, c_type, c_btn = st.columns([3, 2, 1])
    with c_search:
        # Agora o placeholder sugere buscar LOJAS
        local_input = st.text_input("Onde você precisa ir todo dia?", placeholder="Ex: Lefties Aveiro, Universidade do Porto...")
    with c_type:
        tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1", "T2"])
    with c_btn:
        st.write(""); st.write("")
        filtrar = st.button("🔍 Buscar Local", use_container_width=True)

# --- 6. LÓGICA DO MAPA (GPS PRECISO) ---
map_center = [39.55, -7.85] 
zoom_start = 7
ponto_referencia = None # Vai guardar o local da loja (Lefties)

# Se o usuário buscou algo
if local_input:
    geolocator = Nominatim(user_agent="ri_beta_finder")
    try:
        # Tenta achar o local exato (Ex: Lefties)
        loc = geolocator.geocode(f"{local_input}, Portugal", timeout=10)
        
        if loc:
            map_center = [loc.latitude, loc.longitude]
            zoom_start = 14 # Zoom bem perto
            ponto_referencia = loc # Guardamos para desenhar o pino preto
            st.toast(f"📍 Localizado: {loc.address}")
        else:
            st.warning("Não encontrei esse local exato. Mostrando visão geral.")
            
    except Exception as e:
        st.error("Erro no GPS. Tente novamente.")

st.divider()

m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)

# 1. DESENHA O PINO DA BUSCA (A LOJA)
if ponto_referencia:
    folium.Marker(
        [ponto_referencia.latitude, ponto_referencia.longitude],
        popup=f"<b>📍 SEU DESTINO</b><br>{ponto_referencia.address}",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(m)
    
    # Desenha um círculo de 2km em volta da loja
    folium.Circle(
        location=[ponto_referencia.latitude, ponto_referencia.longitude],
        radius=2000, # 2km
        color="black",
        fill=True,
        fill_opacity=0.05
    ).add_to(m)

# 2. DESENHA OS IMÓVEIS (AS CASAS)
marker_cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            
            # Se tiver filtro de local e achamos um ponto, podemos filtrar visualmente?
            # Por enquanto mostramos todos para encher o mapa, mas o foco está na loja
            
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            
            html = f"""
            <div class="popup-card">
                <img src="{img}" class="popup-img">
                <div class="popup-body">
                    <div class="popup-price">{preco}</div>
                    <div class="popup-title">{row.get('titulo','')[:45]}...</div>
                    <a href="{row.get('link')}" target="_blank" class="popup-btn">Ver Anúncio</a>
                </div>
            </div>
            """
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="blue", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=600, returned_objects=[])

# --- 7. RODAPÉ DE LEADS ---
st.write("---")
st.header("🚀 Lista de Fundadores")
st.write("Garanta acesso vitalício ao preço de lançamento.")
with st.form("lista_espera"):
    c1, c2 = st.columns(2)
    with c1: e = st.text_input("E-mail")
    with c2: cid = st.text_input("Cidade")
    if st.form_submit_button("✅ Entrar na Lista") and e and supabase:
        supabase.table("alertas_clientes").insert({"user_id": e, "termo_busca": cid, "ativo": True, "plano": "beta"}).execute()
        st.balloons()