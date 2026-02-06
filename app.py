import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS MAIS VIBRANTE E COLORIDO
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Cores mais vivas no Header */
    h1 { color: #2e86de; } 
    
    .badge-pro {
        background-color: #2e86de; color: white; padding: 4px 8px;
        border-radius: 4px; font-weight: bold; font-size: 12px;
    }
    .stButton>button {
        background-color: #ff4757; color: white; border-radius: 8px; font-weight: 600; border: none;
    }
    .stButton>button:hover {
        background-color: #ff6b81;
    }
    .popup-card { width: 220px; font-family: sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO & SESSÃO ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'
if 'user_name' not in st.session_state: st.session_state['user_name'] = ''

# --- 3. BARRA LATERAL (LOGIN) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)

if not st.session_state['logged_in']:
    st.sidebar.header("🔐 Área do Membro")
    with st.sidebar.form("login"):
        email = st.text_input("E-mail")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar") and supabase:
            res = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
            if res.data:
                user = res.data[0]
                st.session_state.update({'logged_in': True, 'user_plan': user['plano'], 'user_name': user['nome']})
                st.rerun()
            else:
                st.error("Dados incorretos.")
    st.sidebar.markdown("---")
    st.sidebar.info("Ainda não é membro? Escolha um plano abaixo.")
else:
    st.sidebar.success(f"Olá, {st.session_state['user_name']}!")
    if st.session_state['user_plan'] == 'pro':
        st.sidebar.markdown("<span class='badge-pro'>💎 PRO ATIVO</span>", unsafe_allow_html=True)
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

# --- 4. HEADER ---
c1, c2 = st.columns([1, 10])
with c2:
    st.title("Receita Imob")
    st.caption("Inteligência Artificial aplicada ao Arrendamento em Portugal.")

if st.session_state['user_plan'] != 'pro':
    st.info("🔒 Modo Visitante: Filtros limitados. Assine o PRO para liberar busca avançada.")

# --- 5. BUSCA ---
with st.container(border=True):
    c1, c2, c3 = st.columns([4, 2, 1])
    with c1:
        local = st.text_input("📍 Onde procura?", placeholder="Ex: Porto, Aveiro, Lisboa...")
    with c2:
        tipos = st.multiselect("Tipos", ["T0", "T1", "T2", "T3+", "Quarto", "Casa"], default=["T1"])
        if len(tipos) > 1 and st.session_state['user_plan'] != 'pro':
            st.toast("🔒 Multi-seleção é exclusivo PRO.", icon="🚫")
            tipos = [tipos[0]]
    with c3:
        st.write(""); st.write("")
        buscar = st.button("🔍 Buscar")

# --- 6. MAPA E DADOS (OTIMIZADO) ---
df = pd.DataFrame()
# Centraliza em Portugal por padrão (mais bonito que no mar)
map_center = [39.5, -8.0]
zoom = 7

if supabase:
    try:
        # Limitamos a 600 para garantir velocidade máxima no carregamento inicial
        query = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(600)
        df = pd.DataFrame(query.execute().data)
        
        if local and not df.empty:
            df = df[df['endereco'].str.contains(local, case=False, na=False)]
            if not df.empty:
                map_center = [df['lat'].mean(), df['lon'].mean()]
                zoom = 12
            else:
                try:
                    loc = Nominatim(user_agent="ri").geocode(f"{local}, Portugal")
                    if loc: map_center = [loc.latitude, loc.longitude]; zoom = 12
                except: pass
    except: st.error("Erro de conexão.")

st.divider()

if not df.empty:
    # MUDANÇA 1: Tiles="OpenStreetMap" (Colorido e Padrão)
    m = folium.Map(location=map_center, zoom_start=zoom, tiles="OpenStreetMap")
    Fullscreen().add_to(m)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df.iterrows():
        if row['lat'] and row['lon'] and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            
            html = f"""
            <div class="popup-card">
                <img src="{img}" style="width:100%; height:120px; object-fit:cover; border-radius:8px 8px 0 0;">
                <div style="padding:10px;">
                    <b style="color: #27ae60; font-size: 14px;">{preco}</b><br>
                    <span style="font-size:12px; font-weight:bold; color: #333;">{row.get('titulo','')[:40]}...</span><br>
                    <a href="{row.get('link')}" target="_blank" style="display:block; background:#3742fa; color:white; text-align:center; padding:6px; margin-top:8px; text-decoration:none; border-radius:4px; font-weight:bold;">Ver Anúncio</a>
                </div>
            </div>
            """
            # MUDANÇA 2: Ícones Coloridos (Azul)
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=html, 
                icon=folium.Icon(color="blue", icon="home", prefix="fa")
            ).add_to(marker_cluster)

    # MUDANÇA 3: OTIMIZAÇÃO DE VELOCIDADE (returned_objects=[])
    # Isso faz o mapa parar de recarregar a cada clique, fica instantâneo.
    st_folium(m, width=None, height=600, returned_objects=[])
    
    st.caption(f"{len(df)} oportunidades encontradas.")
else:
    st.info("Nenhum imóvel encontrado aqui. Tente outra cidade.")

# --- 7. PAGAMENTO (UPSELL) ---
st.divider()
with st.expander("💎 Desbloquear PRO - €9,90 (Pagamento Único)"):
    st.markdown("### 🚀 Chegue na frente!")
    st.write("O mercado voa. Com o PRO você recebe alertas por e-mail no segundo que o imóvel sai.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.info("📱 **MB WAY**")
        st.markdown(f"**352 924 914 745**") 
        st.caption("Envie o comprovativo abaixo.")
    with c2:
        st.info("🏦 **IBAN**")
        st.markdown("**PT50 0004 5871 9404 1072 2460 51**") # Formatado para leitura fácil
        st.caption("Ana Claudia Campos Dias")
    
    with st.form("pagamento"):
        email_pag = st.text_input("Seu E-mail de Cadastro")
        st.file_uploader("Comprovativo")
        if st.form_submit_button("✅ Enviar Pedido") and email_pag and supabase:
            supabase.table("alertas_clientes").insert({
                "user_id": email_pag, "termo_busca": "PENDENTE PAGAMENTO", "ativo": False, "plano": "aguardando"
            }).execute()
            st.success("Recebido! Liberaremos seu acesso em breve.")