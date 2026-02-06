import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests
import numpy as np

# --- 1. CONFIGURAÇÃO E CSS "MODO LANÇAMENTO" ---
st.set_page_config(page_title="Lugar", page_icon="📍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Poppins', sans-serif;}

    /* ESCONDER INTERFACE DE DESENVOLVEDOR */
    [data-testid="stHeader"], [data-testid="stToolbar"], .stDeployButton, footer, #MainMenu {display: none !important;}
    .block-container {padding-top: 1rem !important; padding-bottom: 0rem !important;}
    
    /* FUNDO PLATINUM */
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); background-attachment: fixed; }

    /* BRANDING */
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 3.5rem; font-weight: 800; letter-spacing: -2px;
    }
    .brand-badge {
        background-color: #2575fc; color: white; padding: 4px 10px;
        border-radius: 12px; font-size: 0.8rem; font-weight: bold;
        vertical-align: middle; position: relative; top: -15px; margin-left: 5px;
    }

    /* COMPONENTES */
    .stTextInput>div>div>input { border-radius: 15px; border: none; padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
    .stButton>button {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        color: white; border: none; border-radius: 15px; height: 3.5em;
        font-weight: 600; box-shadow: 0 4px 15px rgba(37, 117, 252, 0.4); width: 100%;
        transition: transform 0.2s;
    }
    .stButton>button:hover { transform: scale(1.02); color: white; }

    /* CARDS DO MAPA */
    .popup-card { width: 220px; border-radius: 15px; overflow: hidden; background: white; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
    .popup-img { width: 100%; height: 130px; object-fit: cover; }
    .popup-body { padding: 12px; }
    .popup-price { color: #6a11cb; font-weight: 800; font-size: 18px; }
    .popup-btn { display: block; background: #000; color: white; text-align: center; padding: 10px; border-radius: 10px; text-decoration: none; font-size: 12px; margin-top: 10px; font-weight: 600; }
    
    div[data-testid="stVerticalBlock"] > div { border: none !important; background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES DE API ---
GOOGLE_API_KEY = "AIzaSyCws8dm1mPhPKdu4VUk7BTBEe25qGZDrb4"
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

@st.cache_data(ttl=300)
def carregar_dados():
    try:
        res = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(2000).execute()
        df = pd.DataFrame(res.data)
        
        # --- ⚡ CORREÇÃO DA "ARANHA" (JITTER REFORÇADO) ⚡ ---
        if not df.empty:
            # Aumentado para ~50 metros de dispersão para evitar sobreposição total
            df['lat'] += np.random.uniform(-0.0004, 0.0004, size=len(df))
            df['lon'] += np.random.uniform(-0.0004, 0.0004, size=len(df))
        return df
    except Exception as e:
        return pd.DataFrame()

def buscar_google(query):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&key={GOOGLE_API_KEY}"
    try:
        r = requests.get(url).json()
        if r['status'] == 'OK':
            loc = r['results'][0]['geometry']['location']
            return loc['lat'], loc['lng'], r['results'][0]['formatted_address']
    except: pass
    return None

# --- 3. INTERFACE PRINCIPAL ---
st.markdown('<div style="text-align: center;"><span class="brand-text">Lugar</span><span class="brand-badge">BETA</span></div>', unsafe_allow_html=True)

df_total = carregar_dados()

c_spacer_l, c_main, c_spacer_r = st.columns([1, 10, 1])
with c_main:
    col_search, col_btn = st.columns([7, 2], vertical_alignment="bottom")
    with col_search:
        local_input = st.text_input("Onde você quer viver?", placeholder="Ex: Figueira da Foz, Aveiro...", label_visibility="collapsed")
    with col_btn:
        buscar = st.button("🔍 Buscar Agora")

# --- 4. LÓGICA DO MAPA ---
map_center = [39.55, -7.85]
zoom_start = 7
ponto_referencia = None

if buscar and local_input:
    res = buscar_google(local_input)
    if res:
        map_center = [res[0], res[1]]
        zoom_start = 14
        ponto_referencia = res
        
        # --- SOLICITAÇÃO AO ROBÔ ---
        cidade = local_input.split(",")[0].strip()
        # Verifica se já temos dados dessa cidade específica
        tem_dados = not df_total.empty and df_total['endereco'].str.contains(cidade, case=False, na=False).any()
        
        if not tem_dados:
            st.warning(f"Enviamos nosso robô para mapear **{cidade}** agora! Volte em 2 min.")
            try:
                supabase.table("demandas").insert({"termo": cidade, "status": "pendente"}).execute()
            except: pass

# Estilo Google Maps
google_tiles = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"

m = folium.Map(location=map_center, zoom_start=zoom_start, tiles=google_tiles, attr="Google")
LocateControl(auto_start=False).add_to(m)
Fullscreen().add_to(m)

if ponto_referencia:
    folium.Marker([ponto_referencia[0], ponto_referencia[1]], icon=folium.Icon(color="black", icon="star", prefix="fa")).add_to(m)
    folium.Circle([ponto_referencia[0], ponto_referencia[1]], radius=1500, color="#6a11cb", fill=True, fill_opacity=0.1).add_to(m)

cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400"
        
        # Formatação segura de preço
        try:
            p_val = float(row['preco'])
            price_display = f"€ {p_val:,.0f}" if p_val > 0 else "Consultar"
        except:
            price_display = "Consultar"
            
        html = f"""<div class="popup-card">
            <img src="{img}" class="popup-img">
            <div class="popup-body">
                <div class="popup-price">{price_display}</div>
                <div style="font-size:12px; font-weight:500; margin-top:5px;">{row['titulo'][:35]}...</div>
                <a href="{row['link']}" target="_blank" class="popup-btn">Ver Detalhes</a>
            </div></div>"""
            
        folium.Marker(
            [row['lat'], row['lon']], 
            popup=html, 
            icon=folium.Icon(color="purple", icon="home", prefix="fa")
        ).add_to(cluster)

st_folium(m, width=None, height=600, returned_objects=[])

# --- 5. CUPOM DE FUNDADOR ---
st.write("---")
col_l, col_r = st.columns(2)
with col_l:
    st.markdown("### 🎟️ Cupom de Fundador (20% OFF)")
    st.write("Quem usa o Beta agora garante desconto vitalício no futuro.")
with col_r:
    with st.form("vip_list"):
        e = st.text_input("Seu melhor E-mail")
        if st.form_submit_button("Garantir Benefício") and e:
            supabase.table("alertas_clientes").insert({"user_id": e, "termo_busca": "FOUNDER", "ativo": True, "plano": "founder"}).execute()
            st.balloons()
            st.success("E-mail cadastrado! Você é oficialmente um Fundador.")