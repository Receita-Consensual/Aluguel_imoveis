import streamlit as st
from supabase import create_client
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Fullscreen, LocateControl
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim

# --- 1. CONFIGURAÇÃO VISUAL & OTIMIZAÇÃO ---
st.set_page_config(
    page_title="Receita Imob",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed" # Barra fechada para focar no mapa
)

# CSS PARA DEIXAR BONITO E RÁPIDO
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Cores Vivas */
    h1 { color: #2e86de; margin-bottom: 0px;} 
    
    /* Card do Imóvel no Mapa */
    .popup-card { width: 220px; font-family: sans-serif; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .popup-img { width: 100%; height: 120px; object-fit: cover; }
    .popup-body { padding: 10px; background: white; }
    .popup-price { color: #27ae60; font-weight: 800; font-size: 15px; }
    .popup-title { font-size: 13px; font-weight: 600; color: #333; margin: 5px 0; line-height: 1.2; }
    .popup-btn { 
        display: block; background: #3742fa; color: white; text-align: center; 
        padding: 8px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 12px; margin-top: 8px;
    }
    .popup-btn:hover { background: #2f3542; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXÃO & CACHE (AQUI ESTÁ O SEGREDO DA VELOCIDADE) ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        return None

supabase = init_connection()

# CACHE DE DADOS (TTL = 600s = 10 minutos)
# Isso impede que o site trave recarregando o banco a cada clique
@st.cache_data(ttl=600)
def carregar_dados():
    if not supabase: return pd.DataFrame()
    try:
        # Limitamos a 500 para garantir que o mapa voe no celular
        response = supabase.table("imoveis").select("*").order("created_at", desc=True).limit(500).execute()
        return pd.DataFrame(response.data)
    except:
        return pd.DataFrame()

# Inicializa Sessão
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'user_plan' not in st.session_state: st.session_state['user_plan'] = 'free'
if 'user_name' not in st.session_state: st.session_state['user_name'] = ''

# --- 3. BARRA LATERAL (LOGIN) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942544.png", width=50)
    
    if not st.session_state['logged_in']:
        st.header("🔐 Área do Membro")
        with st.form("login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                # Simulação simples de login para velocidade (ou consulta real)
                try:
                    res = supabase.table("usuarios").select("*").eq("email", email).eq("senha", senha).execute()
                    if res.data:
                        user = res.data[0]
                        st.session_state.update({'logged_in': True, 'user_plan': user['plano'], 'user_name': user['nome']})
                        st.rerun()
                    else:
                        st.error("Login inválido.")
                except:
                    st.error("Erro de conexão.")
        st.info("💡 Dica: Assine o PRO para alertas em tempo real.")
    else:
        st.success(f"Olá, {st.session_state['user_name']}!")
        if st.session_state['user_plan'] == 'pro':
            st.markdown("💎 **PLANO PRO ATIVO**")
        if st.button("Sair"):
            st.session_state.clear()
            st.rerun()

# --- 4. HEADER & PESQUISA ---
col_logo, col_title = st.columns([1, 10])
with col_title:
    st.title("Receita Imob")
    st.markdown("**Encontre o imóvel antes de todo mundo.** Monitoramento 24h.")

# Carrega dados do Cache (Instantâneo)
df_total = carregar_dados()

# Filtros
with st.container(border=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        local_input = st.text_input("📍 Onde você quer morar?", placeholder="Ex: Aveiro, Porto...")
    with c2:
        tipos = st.multiselect("Tipo", ["T1", "T2", "T3", "Quarto", "Casa"], default=["T1"])
        if len(tipos) > 1 and st.session_state['user_plan'] != 'pro':
            st.toast("🔒 Multi-seleção é exclusivo PRO.", icon="🚫")
            tipos = [tipos[0]]
    with c3:
        st.write(""); st.write("")
        filtrar = st.button("🔍 Buscar", use_container_width=True)

# --- 5. LÓGICA DO MAPA (OTIMIZADA) ---
map_center = [39.5, -8.0] # Centro Portugal
zoom_start = 7
df_show = df_total.copy()

# Filtro Local (Python puro, super rápido)
if local_input and not df_show.empty:
    df_show = df_show[df_show['endereco'].str.contains(local_input, case=False, na=False)]
    if not df_show.empty:
        map_center = [df_show['lat'].mean(), df_show['lon'].mean()]
        zoom_start = 12
    else:
        # Geocoding só se não achar no banco (economiza tempo)
        try:
            loc = Nominatim(user_agent="ri_app").geocode(f"{local_input}, Portugal")
            if loc: map_center = [loc.latitude, loc.longitude]; zoom_start = 13
        except: pass

st.divider()

if not df_show.empty:
    # Tiles="OpenStreetMap" é o mais rápido e colorido
    m = folium.Map(location=map_center, zoom_start=zoom_start, tiles="OpenStreetMap")
    
    # Plugins úteis
    Fullscreen().add_to(m)
    LocateControl().add_to(m) # Botão "Minha Localização"
    
    # Cluster (Agrupa bolinhas para não travar)
    marker_cluster = MarkerCluster().add_to(m)

    # Renderiza marcadores
    for _, row in df_show.iterrows():
        if row['lat'] and row['lon'] and row['lat'] != 0:
            img = row.get('imagem') or "https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&w=400&q=80"
            preco = f"€ {row['preco']:,.0f}" if row.get('preco', 0) > 0 else "Sob Consulta"
            
            # HTML Otimizado (Sem CSS complexo inline)
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

    # RENDERIZAÇÃO LEVE (returned_objects=[])
    st_folium(m, width=None, height=600, returned_objects=[])
    
    st.caption(f"Mostrando {len(df_show)} oportunidades recentes.")

else:
    st.info("Nenhum imóvel encontrado com esses filtros. Tente outra cidade.")

# --- 6. PAGAMENTO (UPSELL) ---
st.write("---")
with st.expander("💎 Quero ser PRO - €9,90 (Vitalício Beta)"):
    st.markdown("### 🚀 Saia na frente da concorrência!")
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
        st.file_uploader("Comprovativo de Pagamento")
        if st.form_submit_button("✅ Enviar e Liberar Acesso") and email_pag and supabase:
            supabase.table("alertas_clientes").insert({
                "user_id": email_pag, "termo_busca": "PENDENTE PAGAMENTO", "ativo": False, "plano": "aguardando"
            }).execute()
            st.balloons()
            st.success("Recebido! Seu acesso será liberado em breve.")