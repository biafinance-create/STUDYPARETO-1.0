import os
import json
import time
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
MODEL_NAME = 'gemini-3.8-flash' 

def chamar_gemini(prompt, json_mode=False):
    """Chama o modelo e tenta novamente de forma automática se o servidor estiver ocupado"""
    config = types.GenerateContentConfig(
        response_mime_type="application/json"
    ) if json_mode else None

    tentativas = 3
    for i in range(tentativas):
        try:
            res = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config
            )
            return res.text
        except Exception as e:
            erro_str = str(e)
            if "503" in erro_str or "UNAVAILABLE" in erro_str or "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                if i < tentativas - 1:
                    time.sleep(4)
                    continue
            raise Exception(f"Erro na comunicação com o modelo {MODEL_NAME}. Detalhe: {e}")

# -----------------------------------------------------------------------------
# GESTÃO DO ESTADO DA SESSÃO (SESSION STATE)
# -----------------------------------------------------------------------------
if 'conteudo_estudo' not in st.session_state:
    st.session_state.conteudo_estudo = ""
if 'resumo_estruturado' not in st.session_state:
    st.session_state.resumo_estruturado = None
if 'simulado' not in st.session_state:
    st.session_state.simulado = []
if 'respostas_usuario' not in st.session_state:
    st.session_state.respostas_usuario = {}
if 'correcoes' not in st.session_state:
    st.session_state.correcoes = {}
if 'meus_estudos' not in st.session_state:
    st.session_state.meus_estudos = {}  # Dicionario para armazenar os estudos salvos

# -----------------------------------------------------------------------------
# INTERFACE COM ABAS
# -----------------------------------------------------------------------------
st.title("📚 Central Inteligente de Aprendizado & Simulados")
st.caption("Versão atualizada: Gestão de Matérias & SRS Ativo")

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 1. Ingestão de Conteúdo",
    "📑 2. Resumo Estruturado",
    "📝 3. Simulado & Repetição Espaçada",
    "📂 4. Meus Estudos Salvos"
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
        
        st.markdown("### 💾 Salvar este Estudo na sua Biblioteca")
        nome_estudo_input = st.text_input("Nome do Estudo / Matéria (ex: Macroeconomia - Cap 1):")
        if st.button("Salvar Estudo na Aba 4"):
            if nome_estudo_input.strip():
                st.session_state.meus_estudos[nome_estudo_input] = {
                    "conteudo": st.session_state.conteudo_estudo,
                    "resumo": st.session_state.resumo_estruturado,
                    "simulado": st.session_state.simulado,
                    "criacao": datetime.now().strftime("%d/%m/%Y"),
                    "revisoes": {"1d": False, "1s": False, "15d": False, "1m": False}
                }
                st.success(f"Estudo '{nome_estudo_input}' salvo com sucesso! Vá para a Aba 4 para gerenciar.")
            else:
                st.warning("Por favor, insira um nome válido para o estudo.")

# =============================================================================
# ABA 2: RESUMO ESTRUTURADO
# =============================================================================
with tab2:
    st.header("Resumo Estruturado e Completo do Material")
    
    if not st.session_state.conteudo_estudo:
        st.info("Por favor, adicione algum material de estudo na **Aba 1** para gerar o resumo.")
    else:
        if st.button("Gerar Resumo Estruturado") or st.session_state.resumo_estruturado:
            if not st.session_state.resumo_estruturado:
                with st.spinner("O Gemini está analisando o material e criando o resumo estruturado..."):
                    try:
                        prompt = f"""
                        Analise o texto abaixo de forma aprofundada e crie um resumo estruturado e completo.
                        Organize o resumo, obrigatoriamente, nos seguintes tópicos:
                        
                        1. **Visão Geral:** Um parágrafo introdutório sobre o tema central.
                        2. **Principais Tópicos:** Os pontos mais importantes detalhados de forma lógica (utilize bullet points).
                        3. **Conceitos Chave:** Definições claras dos termos fundamentais abordados.
                        4. **Conclusão / Aplicação Prática:** Uma síntese do material e como esse conhecimento é aplicado.

                        Texto base:
                        {st.session_state.conteudo_estudo}
                        """
                        resumo_texto = chamar_gemini(prompt)
                        st.session_state.resumo_estruturado = resumo_texto
                    except Exception as e:
                        st.error(f"Erro ao gerar o resumo: {e}")
            
            if st.session_state.resumo_estruturado:
                st.markdown(st.session_state.resumo_estruturado)

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
                    {"Intervalo": "15 Dias", "Data Prevista": (hoje + timedelta(days=15)).strftime("%d/%m/%Y"), "Foco": "Fixação de conceitos fundamentais"},
                    {"Intervalo": "1 Mês", "Data Prevista": (hoje + timedelta(days=30)).strftime("%d/%m/%Y"), "Foco": "Revisão geral e manutenção"}
                ]
                
                df_cronograma = pd.DataFrame(cronograma)
                st.subheader("📅 Seu Cronograma Automático de Revisão Espaçada (SRS)")
                st.table(df_cronograma)

# =============================================================================
# ABA 4: MEUS ESTUDOS SALVOS & REVISÃO ESPAÇADA PERSONALIZADA
# =============================================================================
with tab4:
    st.header("📂 Meus Estudos Salvos & Acompanhamento de Evolução")
    
    if not st.session_state.meus_estudos:
        st.info("Nenhum estudo salvo ainda. Carregue um material na **Aba 1**, gere o conteúdo e clique em 'Salvar Estudo na Aba 4'.")
    else:
        estudo_selecionado = st.selectbox("Selecione o Estudo para Revisar:", list(st.session_state.meus_estudos.keys()))
        
        if estudo_selecionado:
            dados = st.session_state.meus_estudos[estudo_selecionado]
            st.markdown(f"### Matéria: **{estudo_selecionado}** *(Criado em: {dados['criacao']})*")
            
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📑 Ver Resumo", "📝 Ver Simulado", "🔄 Revisão Espaçada & Evolução"])
            
            with sub_tab1:
                st.subheader("Resumo Estruturado do Estudo")
                if dados['resumo']:
                    st.markdown(dados['resumo'])
                else:
                    st.warning("Nenhum resumo gerado para este estudo. Gere o resumo na Aba 2 antes de salvar.")
            
            with sub_tab2:
                st.subheader("Simulado Salvo")
                if dados['simulado']:
                    st.success(f"Este estudo possui um simulado de {len(dados['simulado'])} questões estruturadas.")
                    for q in dados['simulado']:
                        st.markdown(f"**Q{q['id']}:** {q['enunciado']}")
                        for letra, opt in q['opcoes'].items():
                            st.text(f"  {letra}) {opt}")
                        st.info(f"Resposta Correta: **{q['resposta_correta']}** - {q['explicacao']}")
                        st.markdown("---")
                else:
                    st.warning("Nenhum simulado gerado para este estudo.")
            
            with sub_tab3:
                st.subheader("Painel de Revisão Espaçada (SRS) & Pontuação")
                
                # Checkboxes de Revisão
                revs = dados['revisoes']
                st.write("Marque as revisões conforme for cumprindo o cronograma:")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    revs['1d'] = st.checkbox("Revisão 1 Dia (25 pts)", value=revs['1d'], key=f"rev_1d_{estudo_selecionado}")
                with c2:
                    revs['1s'] = st.checkbox("Revisão 1 Semana (25 pts)", value=revs['1s'], key=f"rev_1s_{estudo_selecionado}")
                with c3:
                    revs['15d'] = st.checkbox("Revisão 15 Dias (25 pts)", value=revs['15d'], key=f"rev_15d_{estudo_selecionado}")
                with c4:
                    revs['1m'] = st.checkbox("Revisão 1 Mês (25 pts)", value=revs['1m'], key=f"rev_1m_{estudo_selecionado}")
                
                # Cálculo da Pontuação de Evolução (0 a 100 pontos)
                pontos = sum([25 for k, v in revs.items() if v])
                
                st.markdown("---")
                st.metric(label="🏆 Pontuação de Evolução neste Estudo", value=f"{pontos} / 100 pts", delta=f"{pontos}% concluído")
                
                if pontos == 100:
                    st.balloons()
                    st.success("🎉 Parabéns! Você concluiu 100% das revisões espaçadas para este estudo. Domínio sólido garantido!")
                elif pontos >= 50:
                    st.info("📈 Bom trabalho! Continue firme no cronograma de consolidação de longo prazo.")
                else:
                    st.warning("⚠️ Atenção: Mantenha as revisões em dia para garantir a retenção na memória de longo prazo.")
