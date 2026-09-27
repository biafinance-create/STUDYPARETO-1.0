import os
import json
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E CHAVE DE API
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Plataforma Integrada de Estudos & Gemini",
    page_icon="📚",
    layout="wide"
)

# Recupera a chave da API do Gemini (Secrets do Streamlit Cloud)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.sidebar.warning("⚠️ Insira sua chave da API do Gemini abaixo para continuar:")
    GEMINI_API_KEY = st.sidebar.text_input("Gemini API Key", type="password")

if not GEMINI_API_KEY:
    st.info("Insira a chave da API do Gemini na barra lateral para ativar as funções do modelo.")
    st.stop()

# Inicializa o cliente oficial da nova SDK do Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

def chamar_gemini(prompt, json_mode=False):
    """Tenta chamar os modelos ativos para a sua conta em sequência."""
    modelos = ['gemini-3.8-flash', 'gemini-3.1-pro-preview']
    
    config = types.GenerateContentConfig(
        response_mime_type="application/json"
    ) if json_mode else None

    ultimo_erro = None
    for m in modelos:
        try:
            res = client.models.generate_content(
                model=m,
                contents=prompt,
                config=config
            )
            return res.text
        except Exception as e:
            ultimo_erro = e
            continue
            
    raise Exception(f"Erro ao conectar aos modelos. Detalhe: {ultimo_erro}")

# -----------------------------------------------------------------------------
# GESTÃO DO ESTADO DA SESSÃO (SESSION STATE)
# -----------------------------------------------------------------------------
if 'conteudo_estudo' not in st.session_state:
    st.session_state.conteudo_estudo = ""
if 'mapa_pareto' not in st.session_state:
    st.session_state.mapa_pareto = None
if 'simulado' not in st.session_state:
    st.session_state.simulado = []
if 'respostas_usuario' not in st.session_state:
    st.session_state.respostas_usuario = {}
if 'correcoes' not in st.session_state:
    st.session_state.correcoes = {}

# -----------------------------------------------------------------------------
# INTERFACE COM ABAS
# -----------------------------------------------------------------------------
st.title("📚 Central Inteligente de Aprendizado & Simulados")

tab1, tab2, tab3 = st.tabs([
    "📥 1. Ingestão de Conteúdo",
    "📊 2. Mapa Pareto & Resumos",
    "📝 3. Simulado & Repetição Espaçada"
])

# =============================================================================
# ABA 1: INGESTÃO DE CONTEÚDO
# =============================================================================
with tab1:
    st.header("Entrada do Material de Estudo")
    
    opcao_ingestao = st.radio(
        "Escolha a fonte do conteúdo:",
        ["Upload de Arquivo (PDF / TXT)", "Texto Direto", "Pesquisa / Geração com Gemini"],
        horizontal=True
    )
    
    if opcao_ingestao == "Upload de Arquivo (PDF / TXT)":
        uploaded_file = st.file_uploader("Envie seu arquivo de estudo", type=["txt", "pdf"])
        if uploaded_file is not None:
            if uploaded_file.type == "text/plain":
                text = uploaded_file.read().decode("utf-8")
                st.session_state.conteudo_estudo = text
                st.success("Arquivo TXT carregado com sucesso!")
            elif uploaded_file.type == "application/pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(uploaded_file)
                    text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                    st.session_state.conteudo_estudo = text
                    st.success("Arquivo PDF extraído e carregado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao ler PDF: {e}")

    elif opcao_ingestao == "Texto Direto":
        texto_digitado = st.text_area(
            "Cole ou digite o material de estudo aqui:",
            value=st.session_state.conteudo_estudo,
            height=300
        )
        if st.button("Salvar Texto"):
            st.session_state.conteudo_estudo = texto_digitado
            st.success("Conteúdo salvo com sucesso!")

    elif opcao_ingestao == "Pesquisa / Geração com Gemini":
        topico_pesquisa = st.text_input("Digite o tema ou assunto que deseja estudar:")
        if st.button("Pesquisar e Gerar Material Completo"):
            if topico_pesquisa.strip():
                with st.spinner("Pesquisando e gerando material com o Gemini..."):
                    try:
                        prompt = f"Gere um material didático, estruturado e aprofundado sobre o seguinte tópico: {topico_pesquisa}."
                        texto_gerado = chamar_gemini(prompt)
                        st.session_state.conteudo_estudo = texto_gerado
                        st.success("Conteúdo gerado pelo Gemini e carregado!")
                    except Exception as e:
                        st.error(f"Erro na comunicação com o Gemini: {e}")
            else:
                st.warning("Insira um tema válido.")

    if st.session_state.conteudo_estudo:
        st.markdown("---")
        st.subheader("Preview do Conteúdo Carregado")
        st.text_area("Texto ativo:", value=st.session_state.conteudo_estudo[:1500] + "...", height=150, disabled=True)

# =============================================================================
# ABA 2: MAPA DE CONCEITOS (PARETO) E RESUMO DETALHADO
# =============================================================================
with tab2:
    st.header("Análise Estratégica pelo Princípio de Pareto (80/20)")
    
    if not st.session_state.conteudo_estudo:
        st.info("Por favor, adicione algum material de estudo na **Aba 1** para gerar o mapa de conceitos.")
    else:
        if st.button("Gerar Mapa de Conceitos (Pareto 80/20)") or st.session_state.mapa_pareto:
            if not st.session_state.mapa_pareto:
                with st.spinner("O Gemini está identificando os conceitos chave de maior impacto..."):
                    try:
                        prompt = f"""
                        Analise o texto abaixo e aplique o Princípio de Pareto (regra 80/20):
                        1. Identifique os 20% de conceitos vitais que representam 80% da compreensão do assunto.
                        2. Para cada conceito, estruture:
                            - **Nome do Conceito**
                            - **Grau de Impacto / Relevância**
                            - **Resumo Detalhado e Explicativo**
                            - **Aplicações Práticas ou Exemplos**

                        Texto base:
                        {st.session_state.conteudo_estudo}
                        """
                        mapa_texto = chamar_gemini(prompt)
                        st.session_state.mapa_pareto = mapa_texto
                    except Exception as e:
                        st.error(f"Erro ao gerar o mapa: {e}")
            
            if st.session_state.mapa_pareto:
                st.markdown(st.session_state.mapa_pareto)

# =============================================================================
# ABA 3: SIMULADO INTERATIVO, CORREÇÃO E REPETIÇÃO ESPAÇADA
# =============================================================================
with tab3:
    st.header("Simulado Interativo & Algoritmo de Repetição Espaçada")
    
    if not st.session_state.conteudo_estudo:
        st.info("Insira o material de estudo na **Aba 1** antes de criar o simulado.")
    else:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            num_questoes = st.slider("Número de Questões", min_value=10, max_value=50, value=10, step=5)
        with col2:
            dificuldade = st.selectbox("Nível de Dificuldade", ["Fácil", "Média", "Complexa", "Mista"])
        with col3:
            st.write(" ")
            st.write(" ")
            gerar_simulado_btn = st.button("🎯 Criar Novo Simulado")

        if gerar_simulado_btn:
            with st.spinner("O Gemini está elaborando o simulado customizado..."):
                prompt = f"""
                Com base no material fornecido, crie um simulado de múltipla escolha com {num_questoes} questões.
                Nível de Dificuldade: {dificuldade}.

                Responda EXCLUSIVAMENTE em formato JSON puro, respeitando a seguinte estrutura:
                [
                    {{
                        "id": 1,
                        "enunciado": "Texto da questão...",
                        "opcoes": {{"A": "Opção A", "B": "Opção B", "C": "Opção C", "D": "Opção D"}},
                        "resposta_correta": "A",
                        "topico_relacionado": "Nome do conceito",
                        "explicacao": "Explicação detalhada da resposta correta.",
                        "lacuna_conceitual": "Descrição da lacuna de aprendizado se o aluno errar esta questão."
                    }}
                ]

                Texto base:
                {st.session_state.conteudo_estudo}
                """
                
                try:
                    json_str = chamar_gemini(prompt, json_mode=True)
                    st.session_state.simulado = json.loads(json_str)
                    st.session_state.respostas_usuario = {}
                    st.session_state.correcoes = {}
                    st.success("Simulado gerado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao estruturar o simulado JSON: {e}")

        if st.session_state.simulado:
            st.markdown("---")
            total_q = len(st.session_state.simulado)
            
            for idx, q in enumerate(st.session_state.simulado):
                q_id = q["id"]
                st.subheader(f"Questão {q_id} de {total_q} | Tópico: *{q['topico_relacionado']}*")
                st.write(q["enunciado"])
                
                opcoes_formatadas = [f"{chave}) {valor}" for chave, valor in q["opcoes"].items()]
                escolha = st.radio(
                    f"Selecione a resposta para a Q{q_id}:",
                    options=opcoes_formatadas,
                    key=f"radio_{q_id}"
                )
                
                col_btn, col_res = st.columns([1, 4])
                
                with col_btn:
                    if st.button(f"Responder Q{q_id}", key=f"btn_{q_id}"):
                        resposta_letra = escolha.split(")")[0]
                        st.session_state.respostas_usuario[q_id] = resposta_letra
                        
                        e_correta = (resposta_letra == q["resposta_correta"])
                        st.session_state.correcoes[q_id] = e_correta
                
                if q_id in st.session_state.correcoes:
                    correto = st.session_state.correcoes[q_id]
                    if correto:
                        st.success(f"✅ **Correto!** {q['explicacao']}")
                    else:
                        st.error(f"❌ **Incorreto!** A resposta correta é a letra **{q['resposta_correta']}**.")
                        st.warning(f"📌 **Lacuna de Aprendizado Detectada:** {q['lacuna_conceitual']}")
                        st.info(f"💡 **Explicação:** {q['explicacao']}")
                
                st.markdown("---")

            if len(st.session_state.correcoes) == total_q:
                total_acertos = sum(1 for v in st.session_state.correcoes.values() if v)
                porcentagem = (total_acertos / total_q) * 100
                
                st.header("📊 Resultado Geral e Cronograma de Repetição Espaçada")
                st.metric(label="Aderência ao Conteúdo (Aproveitamento)", value=f"{porcentagem:.1f}%", delta=f"{total_acertos}/{total_q} acertos")
                
                if porcentagem >= 85:
                    nivel_aderencia = "Alta Aderência (Domínio Sólido)"
                elif porcentagem >= 60:
                    nivel_aderencia = "Média Aderência (Atenção em Pontos Específicos)"
                else:
                    nivel_aderencia = "Baixa Aderência (Necessita Revisão Profunda)"
                
                st.write(f"**Classificação:** {nivel_aderencia}")
                
                hoje = datetime.now()
                cronograma = [
                    {"Intervalo": "1 Dia", "Data Prevista": (hoje + timedelta(days=1)).strftime("%d/%m/%Y"), "Foco": "Reforço das lacunas e erros"},
                    {"Intervalo": "1 Semana", "Data Prevista": (hoje + timedelta(weeks=1)).strftime("%d/%m/%Y"), "Foco": "Consolidação de memória de curto prazo"},
                    {"Intervalo": "15 Dias", "Data Prevista": (hoje + timedelta(days=15)).strftime("%d/%m/%Y"), "Foco": "Fixação de conceitos Pareto"},
                    {"Intervalo": "1 Mês", "Data Prevista": (hoje + timedelta(days=30)).strftime("%d/%m/%Y"), "Foco": "Revisão geral e manutenção"}
                ]
                
                df_cronograma = pd.DataFrame(cronograma)
                st.subheader("📅 Seu Cronograma Automático de Revisão Espaçada (SRS)")
                st.table(df_cronograma)
