"""
Projeto Integrador — "Números que Falam: Descobrindo o Brasil"
Tema do Grupo: Crescimento Demográfico (Persona: Prefeitos de Capitais)

Integrante: JÚLIA
Indicador individual: Identificação de Cidades Outliers (que cresceram muito ou encolheram)
Fonte: IBGE, Censo Demográfico 2010 e 2022.

Como rodar localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from estatisticas import resumo_estatistico, detectar_outliers, classificar_outlier, formatar_numero

st.set_page_config(page_title="Outliers de Crescimento | Júlia", page_icon="🎯", layout="wide")

CAMINHO_DADOS_PADRAO = "dados/capitais_crescimento_2010_2022.csv"

PERSONAS = {
    "Curitiba": "Carlos", "Porto Alegre": "Eduardo", "Belo Horizonte": "Elisa",
    "Salvador": "Jorge", "Florianopolis": "Roberto",
}


@st.cache_data
def carregar_dados_padrao() -> pd.DataFrame:
    return pd.read_csv(CAMINHO_DADOS_PADRAO)


def tratar_dados(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    for c in ["populacao_2010", "populacao_2022", "variacao_absoluta", "taxa_crescimento_pct"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["populacao_2010", "populacao_2022"])
    df["taxa_crescimento_pct"] = ((df["populacao_2022"] - df["populacao_2010"]) / df["populacao_2010"] * 100).round(2)
    df["e_capital_do_grupo"] = df["cidade"].isin(PERSONAS.keys())
    return df


st.sidebar.title("⚙️ Filtros")
st.sidebar.caption("Projeto Integrador • Identificação de Cidades Outliers")

arquivo = st.sidebar.file_uploader("Upload da base IBGE (CSV ou XLSX)", type=["csv", "xlsx"])
if arquivo is not None:
    try:
        df_bruto = pd.read_excel(arquivo) if arquivo.name.endswith(".xlsx") else pd.read_csv(arquivo)
        st.sidebar.success("Arquivo carregado com sucesso!")
    except Exception as e:
        st.sidebar.error(f"Erro ao ler o arquivo: {e}")
        df_bruto = carregar_dados_padrao()
else:
    df_bruto = carregar_dados_padrao()
    st.sidebar.info("Usando a base padrão do IBGE (Censo 2010/2022).")

df = tratar_dados(df_bruto)

regioes = sorted(df["regiao"].dropna().unique().tolist())
regiao_sel = st.sidebar.multiselect("Região", regioes, default=regioes)
df_f = df[df["regiao"].isin(regiao_sel)]

multiplicador = st.sidebar.slider(
    "Sensibilidade do teste de outliers (multiplicador do IQR)", min_value=1.0, max_value=3.0, value=1.5, step=0.1,
    help="A regra clássica usa 1,5×IQR. Valores maiores tornam o critério mais rígido (menos outliers).",
)

if df_f.empty:
    st.warning("Nenhum dado para os filtros selecionados.")
    st.stop()

# --------------------------------------------------------------------------------------
st.title("🎯 Identificação de Cidades Outliers de Crescimento")
st.caption("Startup de Análise de Dados • Consultoria para Prefeitos de Capitais • Responsável: **Júlia**")

with st.expander("📋 Cenário da persona (clique para ler)"):
    st.markdown(
        """
        Antes de revisar os Planos Diretores, os prefeitos pedem à consultoria: **"onde estão os
        casos fora da curva?"** — cidades que cresceram de forma explosiva (pressão sobre
        infraestrutura, saneamento, mobilidade) ou que encolheram (ociosidade de equipamentos
        públicos, evasão econômica). Esta seção aplica a **regra estatística do IQR** para
        responder com rigor, sem depender de impressão subjetiva.
        """
    )

# --------------------------------------------------------------------------------------
# ESTATÍSTICA DESCRITIVA COMPLETA
# --------------------------------------------------------------------------------------
stats = resumo_estatistico(df_f["taxa_crescimento_pct"])
st.subheader("📊 Resumo estatístico — Taxa de crescimento (%) 2010–2022")

linha1 = st.columns(4)
linha1[0].metric("Média", f"{formatar_numero(stats['media'])}%")
linha1[1].metric("Mediana", f"{formatar_numero(stats['mediana'])}%")
linha1[2].metric("Moda", f"{formatar_numero(stats['moda'])}%" if pd.notna(stats["moda"]) else "-")
linha1[3].metric("Desvio padrão", f"{formatar_numero(stats['desvio_padrao'])}%")

linha2 = st.columns(4)
linha2[0].metric("Q1", f"{formatar_numero(stats['q1'])}%")
linha2[1].metric("Q2 (mediana)", f"{formatar_numero(stats['q2'])}%")
linha2[2].metric("Q3", f"{formatar_numero(stats['q3'])}%")
linha2[3].metric("IQR (Q3−Q1)", f"{formatar_numero(stats['iqr'])}%")

linha3 = st.columns(3)
linha3[0].metric("Amplitude (máx−mín)", f"{formatar_numero(stats['amplitude'])} p.p.")
linha3[1].metric("Variância", formatar_numero(stats["variancia"]))
linha3[2].metric("Limites do IQR", f"[{formatar_numero(stats['limite_inferior_outlier'])}%, {formatar_numero(stats['limite_superior_outlier'])}%]")

# Limites recalculados conforme o multiplicador escolhido pelo usuário
lim_inf_custom = stats["q1"] - multiplicador * stats["iqr"]
lim_sup_custom = stats["q3"] + multiplicador * stats["iqr"]

# --------------------------------------------------------------------------------------
# DETECÇÃO DE OUTLIERS
# --------------------------------------------------------------------------------------
st.subheader(f"🚨 Cidades Outliers (regra {multiplicador:.1f} × IQR)")

df_f = df_f.copy()
df_f["classificacao"] = df_f["taxa_crescimento_pct"].apply(
    lambda v, q1=stats["q1"], q3=stats["q3"], iqr=stats["iqr"]: classificar_outlier(v, q1, q3, iqr)
    if multiplicador == 1.5 else (
        "Outlier superior (muito acima do padrão)" if v > lim_sup_custom else
        "Outlier inferior (muito abaixo do padrão)" if v < lim_inf_custom else
        "Dentro do padrão"
    )
)

outliers_sup = df_f[df_f["taxa_crescimento_pct"] > lim_sup_custom].sort_values("taxa_crescimento_pct", ascending=False)
outliers_inf = df_f[df_f["taxa_crescimento_pct"] < lim_inf_custom].sort_values("taxa_crescimento_pct")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**🔺 Outliers superiores — cresceram muito acima do esperado (> {formatar_numero(lim_sup_custom)}%)**")
    if outliers_sup.empty:
        st.success("Nenhuma cidade nesta categoria.")
    else:
        st.dataframe(
            outliers_sup[["cidade", "uf", "taxa_crescimento_pct"]].rename(
                columns={"cidade": "Cidade", "uf": "UF", "taxa_crescimento_pct": "Crescimento (%)"}
            ),
            use_container_width=True, hide_index=True,
        )
with col2:
    st.markdown(f"**🔻 Outliers inferiores — encolheram muito abaixo do esperado (< {formatar_numero(lim_inf_custom)}%)**")
    if outliers_inf.empty:
        st.success("Nenhuma cidade nesta categoria.")
    else:
        st.dataframe(
            outliers_inf[["cidade", "uf", "taxa_crescimento_pct"]].rename(
                columns={"cidade": "Cidade", "uf": "UF", "taxa_crescimento_pct": "Crescimento (%)"}
            ),
            use_container_width=True, hide_index=True,
        )

# --------------------------------------------------------------------------------------
# GRÁFICOS
# --------------------------------------------------------------------------------------
st.subheader("📉 Visualizações")
tab1, tab2 = st.tabs(["Boxplot com outliers", "Dispersão (Z-score visual)"])

with tab1:
    fig_box = px.box(
        df_f, y="taxa_crescimento_pct", points="all", hover_data=["cidade", "uf"],
        labels={"taxa_crescimento_pct": "Crescimento acumulado 2010–2022 (%)"},
        title="Boxplot da taxa de crescimento — pontos fora dos bigodes são outliers",
    )
    st.plotly_chart(fig_box, use_container_width=True)

with tab2:
    df_f["desvio_da_mediana"] = df_f["taxa_crescimento_pct"] - stats["mediana"]
    fig_scatter = px.bar(
        df_f.sort_values("desvio_da_mediana"), x="desvio_da_mediana", y="cidade", orientation="h",
        color="classificacao",
        color_discrete_map={
            "Outlier superior (muito acima do padrão)": "#d62728",
            "Outlier inferior (muito abaixo do padrão)": "#ff7f0e",
            "Dentro do padrão": "#1f77b4",
            "Sem dado": "#7f7f7f",
        },
        labels={"desvio_da_mediana": "Desvio em relação à mediana (p.p.)", "cidade": "", "classificacao": "Classificação"},
        title="Desvio de cada capital em relação à mediana do grupo",
        height=750,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# --------------------------------------------------------------------------------------
# RESPOSTA ÀS PERGUNTAS DE NEGÓCIO
# --------------------------------------------------------------------------------------
st.subheader("💼 Resposta às Perguntas de Negócio da Persona")
total_outliers = len(outliers_sup) + len(outliers_inf)
st.markdown(
    f"""
1. **Onde estão situados os outliers de crescimento?**
   Com a regra de **{multiplicador:.1f}×IQR**, foram identificadas **{total_outliers} cidades
   outliers** em {len(df_f)} capitais analisadas: **{len(outliers_sup)}** cresceram muito
   acima do padrão (destaque para {', '.join(outliers_sup['cidade'].tolist()) if not outliers_sup.empty else 'nenhuma'})
   e **{len(outliers_inf)}** encolheram muito abaixo do padrão
   ({', '.join(outliers_inf['cidade'].tolist()) if not outliers_inf.empty else 'nenhuma'}).

2. **Por que isso importa para o orçamento público?**
   Outliers superiores pressionam **infraestrutura, saneamento e mobilidade** acima da
   capacidade planejada — risco de déficit de serviços. Outliers inferiores indicam
   **ociosidade de equipamentos públicos** (escolas, postos de saúde dimensionados para uma
   população que não existe mais) e possível evasão econômica — risco de gasto ineficiente.
   Tratar as demais cidades pela mediana (não pela média) evita que esses extremos distorçam
   o diagnóstico de "crescimento típico" das capitais brasileiras.
    """
)

# --------------------------------------------------------------------------------------
# CONTEÚDO ADICIONAL
# --------------------------------------------------------------------------------------
st.subheader("📰 Conteúdo adicional")
st.markdown(
    """
    **🔗 Censo 2022: Boa Vista e Florianópolis têm aumento populacional superior a 20% em 12 anos**
    *CNN Brasil* [Ler reportagem](https://www.cnnbrasil.com.br/nacional/censo-2022-boa-vista-e-florianopolis-tem-aumento-populacional-superior-a-20-em-12-anos/)

    **🔗 Censo 2022: saiba o que explica a queda populacional em diferentes capitais do país**
    *Itatiaia* [Ler reportagem](https://www.itatiaia.com.br/brasil/censo-2022-saiba-o-que-explica-a-queda-populacional-em-diferentes-capitais-do-pais/)
    """
)

st.divider()
st.caption(
    "Fonte dos dados: IBGE, Censo Demográfico 2010 e 2022. "
    "Desenvolvido por Júlia • Projeto Integrador — Python & Matemática."
)
