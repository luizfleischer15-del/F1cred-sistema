import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="F1 Cred - Sistema de Gestão", layout="wide", page_icon="🏁")

# --- ESTILIZAÇÃO CUSTOMIZADA (F1 CRED COLORS) ---
st.markdown("""
    <style>
        .stApp { background-color: #f8f9fa; }
        [data-testid="stSidebar"] { background-color: #0A2B4C; }
        [data-testid="stSidebar"] * { color: white; }
        .stButton>button {
            background-color: #FF4B4B;
            color: white;
            border-radius: 5px;
            height: 3em;
            width: 100%;
            font-weight: bold;
        }
        .main-card {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metric-box {
            background-color: #0A2B4C;
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('f1cred_v3.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS propostas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  data TEXT, cliente TEXT, cpf TEXT, convenio TEXT, 
                  valor_total REAL, parcela REAL, comissao REAL, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.markdown("<h1 style='text-align: center; color: #0A2B4C;'>🏁 F1 Cred - Acesso Interno</h1>", unsafe_allow_html=True)
    with st.container():
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            if st.button("Acessar Sistema"):
                if usuario == "admin" and senha == "f1cred2026":
                    st.session_state.logado = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

if not st.session_state.logado:
    tela_login()
    st.stop()

# --- LÓGICA DE CÁLCULO ---
def calcular_virada(salario_atual, tipo):
    # Projeções para 2026
    MINIMO_ATUAL = 1412.00 # Base 2024 para referência
    MINIMO_NOVO = 1518.00  # Exemplo de valor reajustado
    INPC = 1.045           # 4.5% para quem ganha acima do mínimo
    
    if tipo == "Salário Mínimo":
        aumento_bruto = MINIMO_NOVO - salario_atual if salario_atual < MINIMO_NOVO else MINIMO_NOVO * 0.07 
    else:
        aumento_bruto = (salario_atual * INPC) - salario_atual
        
    margem_nova = aumento_bruto * 0.35
    # Coeficiente aproximado para taxa 1.65% em 84x
    valor_saque = (margem_nova * (1 - (1 + 0.0165)**-84)) / 0.0165
    return aumento_bruto, margem_nova, valor_saque

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown("## 🏁 F1 CRED")
    st.markdown("---")
    aba = st.radio("Navegação", ["🏠 Home / Dashboard", "➕ Nova Proposta", "📈 Calculadora de Virada", "📂 Histórico de Clientes"])
    if st.button("Sair"):
        st.session_state.logado = False
        st.rerun()

# --- CONTEÚDO ---
if aba == "🏠 Home / Dashboard":
    st.title("📊 Painel Comercial")
    
    conn = sqlite3.connect('f1cred_v3.db')
    df = pd.read_sql("SELECT * FROM propostas", conn)
    conn.close()
    
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Produção Total", f"R$ {df['valor_total'].sum():,.2f}")
        with c2: st.metric("Comissão Bruta", f"R$ {df['comissao'].sum():,.2f}")
        with c3: st.metric("Propostas", len(df))
        with c4: 
            pago = df[df['status'] == 'Paga']['valor_total'].sum()
            st.metric("Total Pago", f"R$ {pago:,.2f}")
            
        st.markdown("### Últimas Operações")
        st.dataframe(df.sort_values(by='id', ascending=False), use_container_width=True)
    else:
        st.info("Nenhuma operação registrada no banco de dados.")

elif aba == "➕ Nova Proposta":
    st.title("📝 Cadastrar Simulação")
    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Cliente")
            cpf = st.text_input("CPF")
            convenio = st.selectbox("Convênio", ["INSS", "SIAPE", "Exército", "Marinha", "Aeronáutica", "Governo", "Prefeitura"])
        with col2:
            valor = st.number_input("Valor do Empréstimo (R$)", min_value=0.0)
            prazo = st.number_input("Prazo", value=84)
            percent_comis = st.slider("Sua Comissão (%)", 0.0, 15.0, 12.0)
            
        taxa = 0.0165
        parcela = (valor * taxa) / (1 - (1 + taxa)**-prazo) if valor > 0 else 0
        v_comissao = valor * (percent_comis / 100)
        
        st.markdown(f"""
            <div style='background-color:#e1f5fe; padding:20px; border-radius:10px; border-left: 5px solid #01579b;'>
                <h4>Resumo do Cálculo:</h4>
                <b>Parcela:</b> R$ {parcela:.2f} | <b>Comissão:</b> R$ {v_comissao:.2f}
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Salvar na Base de Dados"):
            if nome and cpf:
                conn = sqlite3.connect('f1cred_v3.db')
                c = conn.cursor()
                c.execute("INSERT INTO propostas (data, cliente, cpf, convenio, valor_total, parcela, comissao, status) VALUES (?,?,?,?,?,?,?,?)",
                          (datetime.now().strftime("%d/%m/%Y"), nome, cpf, convenio, valor, parcela, v_comissao, "Simulação"))
                conn.commit()
                conn.close()
                st.success("✅ Proposta salva com sucesso!")
            else:
                st.warning("Preencha Nome e CPF para salvar.")

elif aba == "📈 Calculadora de Virada":
    st.title("📈 Reajuste de Margem (Virada de Ano)")
    st.markdown("Cálculo para clientes com margem 100% comprometida.")
    
    col1, col2 = st.columns(2)
    with col1:
        tipo_b = st.selectbox("Tipo de Reajuste", ["Salário Mínimo", "Acima do Mínimo (INPC)"])
        sal_atual = st.number_input("Salário Atual do Cliente (R$)", value=1412.0)
    
    aumento, margem, saque = calcular_virada(sal_atual, tipo_b)
    
    with col2:
        st.markdown(f"""
            <div class='metric-box'>
                <p>Aumento Real no Salário</p>
                <h2>R$ {aumento:.2f}</h2>
            </div><br>
            <div class='metric-box' style='background-color: #2e7d32;'>
                <p>Nova Margem Disponível (35%)</p>
                <h2>R$ {margem:.2f}</h2>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader(f"💰 Valor estimado de LIBERAÇÃO: R$ {saque:.2f}")
    st.caption("Cálculo estimado com taxa de 1,65% em 84 parcelas.")

elif aba == "📂 Histórico de Clientes":
    st.title("📂 Base de Dados Completa")
    conn = sqlite3.connect('f1cred_v3.db')
    df = pd.read_sql("SELECT * FROM propostas", conn)
    conn.close()
    
    if not df.empty:
        # Filtro de busca
        busca = st.text_input("🔍 Buscar por Nome ou CPF")
        if busca:
            df = df[df['cliente'].str.contains(busca, case=False) | df['cpf'].contains(busca)]
        
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exportar para Excel (CSV)", csv, "relatorio_f1cred.csv", "text/csv")
    else:
        st.info("Nenhum dado encontrado.")
