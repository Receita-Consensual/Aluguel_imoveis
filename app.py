import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS LIMPO E MODERNO
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
        display: block; background: #3742fa; color: white; text-align: center; 
        padding: 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 12px; margin-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO & CACHE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

@st.cache_data(ttl=300) # Cache de 5 min para ser rápido
def carregar_dados():
    if not supabase: return pd.DataFrame()
    try:
        # Traz dados e JÁ FILTRA o que tem latitude 0 (Oceano)
        response = supabase.table("imoveis").select("*").neq("lat", 0).order("created_at", desc=True).limit(600).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

# Inicializa Sessão
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'
if 'user_name' not in st.session_state: st.session_state['user_name'] = ''

# --- 3. LOGIN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)
    if not st.session_state['logged_in']:
        st.header("🔐 Área do Membro")
        with st.form("login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar") and supabase:
                try:
                    res = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
                    if res.data:
                        user = res.data[0]
                        st.session_state.update({'logged_in': True, 'user_plan': user['plano'], 'user_name': user['nome']})
                        st.rerun()
                    else: st.error("Login inválido.")
                except: st.error("Erro conexão.")
    else:
        st.success(f"Olá, {st.session_state['user_name']}!")
        if st.session_state['user_plan'] == 'pro': st.markdown("💎 **PRO ATIVO**")
        if st.button("Sair"): st.session_state.clear(); st.rerun()

# --- 4. HEADER & PESQUISA ---
c1, c2 = st.columns([1, 10])
with c2:
    st.title("Receita Imob")
    st.markdown("📍 **O único mapa que encontra aluguel antes de ser anunciado.**")

df_total = carregar_dados()

# Filtros
with st.container(border=True):
    c_search, c_type, c_btn = st.columns([3, 2, 1])
    with c_search:
        local_input = st.text_input("Para onde vamos?", placeholder="Ex: Aveiro, Porto, Matosinhos...")
    with c_type:
        tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1"])
        if len(tipos) > 1 and st.session_state['user_plan'] != 'pro':
            st.toast("🔒 Multi-seleção é exclusivo PRO.", icon="🚫")
            tipos = [tipos[0]]
    with c_btn:
        st.write(""); st.write("")
        filtrar = st.button("🔍 Buscar", use_container_width=True)

# --- 5. LÓGICA DO MAPA (ANTI-OCEANO) ---

# Padrão: Centro de Portugal (Santarém) - NUNCA OCEANO
map_center = [39.5572, -7.8536] 
zoom_start = 7
df_show = df_total.copy()

# 1. Filtra Dados do Banco
if local_input and not df_show.empty:
    df_show = df_show[df_show['endereco'].str.contains(local_input, case=False, na=False)]

# 2. Define o Centro do Mapa
if local_input:
    # Se achou imóveis, centraliza neles
    if not df_show.empty:
        map_center = [df_show['lat'].mean(), df_show['lon'].mean()]
        zoom_start = 12
    else:
        # Se NÃO achou imóveis, usa Geocoding para levar o mapa até a cidade vazia
        # Isso evita ficar no mar ou no centro padrão
        try:
            loc = Nominatim(user_agent="ri_fix").geocode(f"{local_input}, Portugal")
            if loc:
                map_center = [loc.latitude, loc.longitude]
                zoom_start = 13
                st.toast(f"Nenhum imóvel encontrado, mas mostrando: {local_input}")
        except: pass

st.divider()

# Cria o Mapa (OpenStreetMap é colorido e rápido)
m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")

# --- TRUQUE DO GPS: auto_start=True ---
# Isso pede a localização do usuário assim que carrega
LocateControl(auto_start=True, strings={"title": "Mostrar minha localização"}).add_to(m)

Fullscreen().add_to(m)
marker_cluster = MarkerCluster().add_to(m)

if not df_show.empty:
    for _, row in df_show.iterrows():
        # GARANTIA FINAL: Só plota se latitude for válida e diferente de 0
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

# Renderiza
st_folium(m, width=None, height=600, returned_objects=[])

if df_show.empty and not local_input:
    st.info("Carregando mapa nacional...")
elif df_show.empty:
    st.warning(f"Ainda não temos imóveis cadastrados em **{local_input}**, mas o robô já começou a procurar.")

# --- 6. PAGAMENTO ---
st.write("---")
with st.expander("💎 Quero ser PRO - €9,90"):
    st.markdown("### 🚀 Saia na frente!")
    st.write("Receba alertas no e-mail assim que o anúncio for publicado.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.success("**MB WAY**")
        st.markdown("### 352 924 914 745") 
        st.caption("Enviar comprovativo abaixo")
    with c2:
        st.info("**IBAN**")
        st.markdown("**PT50 0004 5871 9404 1072 2460 51**")
        st.caption("Ana Claudia Campos Dias")
    
    with st.form("pagamento"):
        email_pag = st.text_input("Seu E-mail")
        st.file_uploader("Comprovativo")
        if st.form_submit_button("✅ Enviar e Liberar") and email_pag and supabase:
            supabase.table("alertas_clientes").insert({
                "user_id": email_pag, "termo_busca": "PENDENTE PAGAMENTO", "ativo": False, "plano": "aguardando"
            }).execute()
            st.balloons()
            st.success("Recebido! Seu acesso será liberado em breve.")