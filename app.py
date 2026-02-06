import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
import requests

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Lugar | Beta",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CHAVES DE API (INTEGRADAS) ---
GOOGLE_API_KEY = "AIzaSyCws8dm1mPhPKdu4VUk7BTBEe25qGZDrb4"
SUPABASE_URL = "https://zprocqmlefzjrepxtxko.supabase.co"
SUPABASE_KEY = "sb_publishable_wPBDEtqfKPrYMD6m6IJzWw_VWL9sVlM"

# --- 3. CSS PREMIUM (VISUAL APP) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;700&display=swap');
    html, body, [class*="css"] {font-family: 'Poppins', sans-serif;}

    /* Fundo Moderno */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        background-attachment: fixed;
    }

    /* Limpeza de Interface */
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container {padding-top: 1rem !important; padding-bottom: 2rem !important;}
    
    /* Branding */
    .brand-text {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 800;
        letter-spacing: -2px;
    }
    .brand-badge {
        background-color: #2575fc; color: white; padding: 4px 10px;
        border-radius: 12px; font-size: 0.8rem; font-weight: bold;
        vertical-align: middle; margin-left: 10px; position: relative; top: -15px;
    }

    /* Inputs e Botões */
    .stTextInput>div>div>input {
        border-radius: 12px; border: none; padding: 12px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .stButton>button {
        background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%);
        color: white; border: none; border-radius: 12px; height: 3em;
        font-weight: 600; box-shadow: 0 4px 15px rgba(37, 117, 252, 0.4);
        width: 100%; transition: transform 0.2s;
    }
    .stButton>button:hover { transform: scale(1.02); color: white; }

    /* Popups Otimizados */
    .popup-card { width: 200px; background: white; border-radius: 8px; overflow: hidden; }
    .popup-img { width: 100%; height: 110px; object-fit: cover; }
    .popup-body { padding: 8px; }
    .popup-price { color: #6a11cb; font-weight: 800; font-size: 15px; }
    .popup-btn { display: block; background: #222; color: white; text-align: center; padding: 6px; border-radius: 6px; text-decoration: none; font-size: 11px; margin-top: 5px; }
    
    div[data-testid="stVerticalBlock"] > div { border: none !important; background: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. CONEXÃO COM BANCO DE DADOS ---
@st.cache_resource
def init_connection():
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

supabase = init_connection()

@st.cache_data(ttl=300)
def carregar_dados():
    if not supabase: return pd.DataFrame()
    try:
        # Busca até 2000 imóveis para garantir volume
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(2000).execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

# --- 5. FUNÇÃO DE BUSCA GOOGLE ---
def buscar_google(query):
    if not query: return None
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={query}&key={GOOGLE_API_KEY}"
    try:
        r = requests.get(url)
        data = r.json()
        if data['status'] == 'OK':
            res = data['results'][0]
            lat = res['geometry']['location']['lat']
            lon = res['geometry']['location']['lng']
            nome = res['formatted_address']
            return lat, lon, nome
    except: pass
    return None

# --- 6. INTERFACE DE BUSCA ---
with st.sidebar:
    st.markdown("### Feedback")
    with st.form("bug_report"):
        desc = st.text_area("Encontrou erro?")
        if st.form_submit_button("Enviar") and supabase:
            supabase.table("alertas_clientes").insert({"user_id": "BUG", "termo_busca": desc, "ativo": False, "plano": "beta_final"}).execute()
            st.success("Obrigado!")

st.markdown("""
<div style="text-align: center; margin-bottom: 20px;">
    <span class="brand-text">Lugar</span><span class="brand-badge">BETA</span>
    <div style="color: #555; font-size: 1.2rem; margin-top: -5px;">Encontre o seu lugar no mundo.</div>
</div>
""", unsafe_allow_html=True)

df_total = carregar_dados()

c_spacer_l, c_main, c_spacer_r = st.columns([1, 10, 1])
with c_main:
    c_search, c_type, c_btn = st.columns([5, 2, 2], vertical_alignment="bottom")
    with c_search:
        local_input = st.text_input("Onde você quer viver?", placeholder="Ex: Glicínias Aveiro, Centro do Rio...", label_visibility="hidden")
    with c_type:
        tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1", "T2"], label_visibility="hidden")
    with c_btn:
        buscar = st.button("🔍 Buscar")

# --- 7. LÓGICA DO MAPA E INTEGRAÇÃO ROBÔ ---
map_center = [39.55, -7.85] 
zoom_start = 6
ponto_referencia = None

if buscar and local_input:
    resultado = buscar_google(local_input)
    
    if resultado:
        lat, lon, nome_completo = resultado
        map_center = [lat, lon]
        zoom_start = 14
        ponto_referencia = (lat, lon, nome_completo)
        
        # --- VERIFICAÇÃO DE DEMANDA (A MÁGICA DO ROBÔ) ---
        # Pega a primeira parte do endereço (Ex: "Figueira da Foz" de "Figueira da Foz, Portugal")
        termo_cidade = local_input.split(",")[0].strip()
        
        # Filtra para ver se JÁ TEMOS imóveis lá
        tem_imoveis = False
        if not df_total.empty:
            # Busca simples no texto do endereço
            filtro = df_total[df_total['endereco'].str.contains(termo_cidade, case=False, na=False)]
            if not filtro.empty:
                tem_imoveis = True
                st.toast(f"📍 {len(filtro)} imóveis encontrados em {termo_cidade}")
        
        if not tem_imoveis:
            # NÃO TEM IMÓVEIS? CHAMA O ROBÔ!
            st.warning(f"🔎 Ainda não temos imóveis em **{termo_cidade}**, mas enviamos nosso robô para lá agora!")
            st.info("⏳ O sistema está buscando dados. Volte em 3 minutos para ver as novidades.")
            
            # Insere o pedido na fila
            if supabase:
                try:
                    supabase.table("demandas").insert({"termo": termo_cidade, "status": "pendente"}).execute()
                except:
                    pass # Evita erro na tela se já tiver pedido
    else:
        st.warning("Local não encontrado. Tente ser mais específico.")

st.write("")

# Renderiza Mapa Google
st.markdown("<div style='box-shadow: 0 10px 30px rgba(0,0,0,0.1); border-radius: 20px; overflow: hidden;'>", unsafe_allow_html=True)

google_tiles = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"

m = folium.Map(
    location=map_center, 
    zoom_start=zoom_start, 
    tiles=google_tiles, 
    attr="Google Maps"
)

LocateControl(auto_start=False).add_to(m)
Fullscreen().add_to(m)

if ponto_referencia:
    folium.Marker([ponto_referencia[0], ponto_referencia[1]], popup="<b>📍 SEU DESTINO</b>", icon=folium.Icon(color="black", icon="star", prefix="fa")).add_to(m)
    folium.Circle([ponto_referencia[0], ponto_referencia[1]], radius=2000, color="#6a11cb", fill=True, fill_opacity=0.1).add_to(m)

marker_cluster = MarkerCluster().add_to(m)

if not df_total.empty:
    for _, row in df_total.iterrows():
        if pd.notnull(row['lat']) and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Ver"
            
            html = f"""<div class="popup-card">
            <img src="{img}" class="popup-img">
            <div class="popup-body">
                <div class="popup-price">{preco}</div>
                <div style="font-size:11px; margin-bottom:5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{row.get('titulo','')[:30]}...</div>
                <a href="{row.get('link')}" target="_blank" class="popup-btn">Ver Detalhes</a>
            </div></div>"""
            
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="purple", icon="home", prefix="fa")
            ).add_to(marker_cluster)

st_folium(m, width=None, height=600, returned_objects=[])
st.markdown("</div>", unsafe_allow_html=True)

# --- 8. LEAD MAGNET (CUPOM) ---
st.write("---")
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown("### 🎟️ Cupom de Fundador")
    st.write("Garanta **20% de desconto vitalício**.")
with c2:
    with st.form("vip_final"):
        col_a, col_b = st.columns(2)
        with col_a: email = st.text_input("E-mail")
        with col_b: nome = st.text_input("Nome")
        if st.form_submit_button("Pegar Desconto") and email and supabase:
            supabase.table("alertas_clientes").insert({"user_id": email, "termo_busca": "GOOGLE_MAPS", "ativo": True, "plano": "founder_final"}).execute()
            st.balloons()
            st.success("Cadastrado com sucesso!")