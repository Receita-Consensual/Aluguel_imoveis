import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
import numpy as np

# --- 1. CONFIGURAÇÃO E IDENTIDADE ---
st.set_page_config(page_title="Lugar", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")

# CSS Customizado para um visual de Startup Profissional
# CSS para garantir legibilidade no telefone e esconder lixo visual
st.markdown("""
    <style>
    /* 1. Reset Total e Fundo */
    [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding: 1rem !important;}
    .stApp { background-color: #ffffff !important; }

    /* 2. Topo: Força a cor do contador (Caption) */
    [data-testid="stCaptionContainer"] {
        color: #1a1a1a !important;
        font-weight: 600 !important;
        text-align: center;
        display: block;
    }

    /* 3. Título Principal */
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        color: #6a11cb; 
        font-size: 2.8rem;
        font-weight: 800;
        text-align: center;
        display: block;
    }

    /* 4. Em Baixo: Estilização do Formulário de Cupom */
    .stForm {
        background-color: #f8f9fa !important;
        border: 1px solid #e0e0e0 !important;
        padding: 20px !important;
        border-radius: 15px !important;
    }

    /* Força cor de todos os textos, títulos e labels */
    h1, h2, h3, p, span, label {
        color: #1a1a1a !important;
    }

    /* Garante que o texto dentro do input de e-mail seja visível */
    .stTextInput input {
        color: #1a1a1a !important;
        background-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CREDENCIAIS ---
GOOGLE_API_KEY = "AIzaSyCws8dm1mPhPKdu4VUk7BTBEe25qGZDrb4"
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- 3. CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=30)
def carregar_dados():
    try:
        res = supabase.table("imoveis").select("*").neq("lat", 0).limit(1000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            # Jitter (Tremor) para espalhar pinos sobrepostos
            df['lat'] += np.random.uniform(-0.0005, 0.0005, size=len(df))
            df['lon'] += np.random.uniform(-0.0005, 0.0005, size=len(df))
        return df
    except:
        return pd.DataFrame()

# --- 4. INTERFACE PRINCIPAL ---
st.markdown('<span class="brand-text">Lugar</span>', unsafe_allow_html=True)
df_total = carregar_dados()

if not df_total.empty:
    st.caption(f"📍 {len(df_total)} imóveis disponíveis em Portugal")
else:
    st.caption("📍 O robô está a povoar o mapa... tente pesquisar uma cidade!")

col_search, col_btn = st.columns([8, 2])
with col_search:
    local_input = st.text_input("Onde quer viver?", placeholder="Ex: Aveiro, Porto...", label_visibility="collapsed")
with col_btn:
    buscar = st.button("🔍 Buscar")

# --- 5. LÓGICA DE BUSCA E LOGS DE PESQUISA ---
map_center = [39.55, -7.85]
zoom_start = 7

if buscar and local_input:
    # REGISTRO DE LOG: Salva o que o usuário pesquisou
    try:
        supabase.table("logs_pesquisas").insert({"termo_buscado": local_input}).execute()
    except: pass

    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={local_input}&key={GOOGLE_API_KEY}"
    r = requests.get(url).json()
    if r['status'] == 'OK':
        loc = r['results'][0]['geometry']['location']
        map_center = [loc['lat'], loc['lng']]
        zoom_start = 14
        cidade = local_input.split(",")[0].strip()
        # Envia demanda para o robô trabalhar naquela cidade
        supabase.table("demandas").insert({"termo": cidade, "status": "pendente"}).execute()

# --- 6. MAPA INTERATIVO ---
google_tiles = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles=google_tiles, attr="Google")
Fullscreen().add_to(m)
LocateControl(auto_start=False).add_to(m)

if not df_total.empty:
    cluster = MarkerCluster().add_to(m)
    for _, row in df_total.iterrows():
        try:
            preco_val = f"€ {float(row['preco']):,.0f}" if row['preco'] else "Ver"
            # O ID do imóvel é passado para facilitar o rastreio no log de cliques
            html = f"""
                <div style='font-family: sans-serif;'>
                    <b>{preco_val}</b><br>
                    <a href='{row['link']}' target='_blank' style='color: #6a11cb;'>Ver Detalhes</a>
                </div>
            """
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="purple", icon="home"),
                custom_id=row['id'] # Atributo para controle interno
            ).add_to(cluster)
        except: continue

# Renderização do mapa e captura de cliques
mapa_data = st_folium(m, width="100%", height=500, returned_objects=["last_object_clicked"])

# --- 7. LOGS DE CLIQUES (TRACKING) ---
# Se o usuário clicar num pino, registramos o evento
if mapa_data.get("last_object_clicked"):
    click_lat = mapa_data["last_object_clicked"]["lat"]
    click_lon = mapa_data["last_object_clicked"]["lng"]
    
    # Encontra qual imóvel foi clicado no DataFrame
    match = df_total[
        (np.isclose(df_total['lat'], click_lat, atol=1e-4)) & 
        (np.isclose(df_total['lon'], click_lon, atol=1e-4))
    ]
    
    if not match.empty:
        imovel_clicado = match.iloc[0]
        # Registra o clique no banco
        try:
            supabase.table("logs_cliques").insert({
                "imovel_id": int(imovel_clicado['id']),
                "titulo_imovel": imovel_clicado['titulo']
            }).execute()
        except: pass

# --- 8. SEÇÃO VIP / CUPOM ---
st.write("---")
c1, c2 = st.columns(2)
with c1:
    st.markdown("### 🎟️ Cupom de Fundador (20% OFF)")
    st.write("Garanta o seu desconto vitalício para quando o Lugar for lançado oficialmente.")
with c2:
    with st.form("vip_final"):
        email = st.text_input("Seu E-mail")
        if st.form_submit_button("Garantir Desconto") and email:
            supabase.table("alertas_clientes").insert({
                "user_id": email, 
                "termo_busca": "FOUNDER", 
                "ativo": True
            }).execute()
            st.balloons()
            st.success("Registado com sucesso!")