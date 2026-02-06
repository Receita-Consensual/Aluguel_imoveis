import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
from streamlit_searchbox import st_searchbox # A BIBLIOTECA MÁGICA

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

# --- 3. FUNÇÃO DE AUTOCOMPLETE (GOOGLE STYLE) ---
def buscar_sugestoes(termo):
    if not termo: return []
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": termo,
        "format": "json",
        "countrycodes": "pt", # Foca em Portugal
        "limit": 5,
        "addressdetails": 1
    }
    headers = {'User-Agent': 'receita_imob_beta'}
    try:
        r = requests.get(url, params=params, headers=headers)
        data = r.json()
        # Retorna lista de tuplas: (Nome que aparece, Valor que o código usa)
        return [(item['display_name'], item) for item in data]
    except:
        return []

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1040/1040993.png", width=50)
    st.title("Central Beta 🚧")
    with st.form("bug_report"):
        nome_bug = st.text_input("Seu Nome")
        desc_bug = st.text_area("O que aconteceu?")
        if st.form_submit_button("🐛 Reportar") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": desc_bug, "ativo": False, "plano": nome_bug}).execute()
            st.success("Enviado!")

# --- 5. HEADER ---
c1, c2 = st.columns([1, 10])
with c2:
    st.title("Receita Imob | Versão Beta")
    st.markdown("""
    <div class="feedback-box">
        🚀 <b>Novo Recurso:</b> Pesquisa Inteligente! Digite o nome da loja ou local e selecione na lista.
    </div>
    """, unsafe_allow_html=True)

df_total = carregar_dados()

# --- 6. BUSCA COM AUTOCOMPLETE ---
with st.container(border=True):
    c_search, c_type = st.columns([3, 1])
    
    with c_search:
        # AQUI ESTÁ A MÁGICA: st_searchbox
        local_selecionado = st_searchbox(
            buscar_sugestoes,
            key="busca_gps",
            placeholder="Digite o local (Ex: Glicínias, Hospital de São João...)",
            clear_on_submit=False
        )

    with c_type:
        st.write("") # Espaço visual
        tipos = st.multiselect("Filtro", ["T1", "T2", "T3", "Quarto"], default=["T1", "T2"])

# --- 7. LÓGICA DO MAPA ---
map_center = [39.55, -7.85] 
zoom_start = 7
ponto_referencia = None 

# Se o usuário SELECIONOU algo na lista (não precisa clicar em botão buscar)
if local_selecionado:
    # local_selecionado já vem com latitude e longitude da API!
    lat_busca = float(local_selecionado['lat'])
    lon_busca = float(local_selecionado['lon'])
    nome_busca = local_selecionado['display_name'].split(",")[0] # Pega só o primeiro nome
    
    map_center = [lat_busca, lon_busca]
    zoom_start = 15 # Zoom bem perto
    ponto_referencia = (lat_busca, lon_busca, nome_busca)
    
    st.toast(f"📍 Indo para: {nome_busca}")

st.divider()

m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
LocateControl(auto_start=True).add_to(m)
Fullscreen().add_to(m)

# 1. PINO DO LOCAL PESQUISADO
if ponto_referencia:
    folium.Marker(
        [ponto_referencia[0], ponto_referencia[1]],
        popup=f"<b>🎯 {ponto_referencia[2]}</b>",
        icon=folium.Icon(color="black", icon="star", prefix="fa")
    ).add_to(m)
    
    folium.Circle(
        location=[ponto_referencia[0], ponto_referencia[1]],
        radius=1500, # 1.5km
        color="black", fill=True, fill_opacity=0.05
    ).add_to(m)

# 2. IMÓVEIS
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

# --- 8. LEAD MAGNET ---
st.write("---")
st.header("🚀 Lista de Fundadores")
with st.form("lista_espera"):
    c1, c2 = st.columns(2)
    with c1: e = st.text_input("E-mail")
    with c2: cid = st.text_input("Cidade")
    if st.form_submit_button("✅ Entrar na Lista") and e and supabase:
        supabase.table("alertas_clientes").insert({"user_id": e, "termo_busca": cid, "ativo": True, "plano": "beta_v2"}).execute()
        st.balloons()