"""Relatório: gera o gráfico e atualiza a seção de indicadores do README."""

import re
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sem interface gráfica (roda no GitHub Actions)
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline.config import SERIES  # noqa: E402

MARCADOR_INICIO = "<!-- INDICADORES:INICIO -->"
MARCADOR_FIM = "<!-- INDICADORES:FIM -->"


def numero_br(valor, casas: int = 2) -> str:
    if valor is None or pd.isna(valor):
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def data_br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _variacao_no_ano(dolar: pd.DataFrame) -> float | None:
    ultima = dolar.iloc[-1]
    ano_anterior = dolar[[d.year < ultima["data"].year for d in dolar["data"]]]
    if ano_anterior.empty:
        return None
    base = ano_anterior.iloc[-1]["valor"]
    return (ultima["valor"] / base - 1) * 100


def gerar_markdown(silver: dict[str, pd.DataFrame], gold: pd.DataFrame, hoje: date) -> str:
    linhas = [
        f"_Última execução do pipeline: {data_br(hoje)}_",
        "",
        "| Indicador | Último valor | Referência |",
        "|---|---|---|",
    ]
    for nome, serie in SERIES.items():
        df = silver[nome]
        ultima = df.iloc[-1]
        casas = 4 if serie.unidade == "R$" else 2
        referencia = ultima["data"].strftime("%m/%Y") if serie.frequencia == "mensal" else data_br(ultima["data"])
        linhas.append(f"| {serie.descricao} | {numero_br(ultima['valor'], casas)} {serie.unidade} | {referencia} |")

    variacao = _variacao_no_ano(silver["dolar"])
    if variacao is not None:
        linhas.append(f"| Variação do dólar no ano | {numero_br(variacao)} % | desde 31/12 do ano anterior |")

    com_ipca_12m = gold.dropna(subset=["ipca_12m"])
    if not com_ipca_12m.empty:
        ref = com_ipca_12m.iloc[-1]
        linhas.append(f"| IPCA acumulado em 12 meses | {numero_br(ref['ipca_12m'])} % | até {ref['mes']} |")
        linhas.append(f"| Juro real aproximado (Selic − IPCA 12m) | {numero_br(ref['juro_real_aprox'])} % a.a. | {ref['mes']} |")

    linhas += [
        "",
        "**Últimos 12 meses (camada gold)**",
        "",
        "| Mês | Dólar médio | Euro médio | Selic meta | IPCA mês | IPCA 12m |",
        "|---|---|---|---|---|---|",
    ]
    for _, linha in gold.tail(12).iloc[::-1].iterrows():
        linhas.append(
            f"| {linha['mes']} | {numero_br(linha['dolar_medio'], 4)} | {numero_br(linha['euro_medio'], 4)} "
            f"| {numero_br(linha['selic_meta'])} | {numero_br(linha['ipca_mes'])} | {numero_br(linha['ipca_12m'])} |"
        )

    linhas += ["", "![Dólar e Selic](data/gold/grafico.png)"]
    return "\n".join(linhas)


def atualizar_readme(caminho_readme: Path, conteudo: str) -> None:
    texto = caminho_readme.read_text(encoding="utf-8")
    padrao = re.compile(re.escape(MARCADOR_INICIO) + r".*?" + re.escape(MARCADOR_FIM), re.DOTALL)
    if not padrao.search(texto):
        raise ValueError(f"Marcadores {MARCADOR_INICIO} / {MARCADOR_FIM} não encontrados em {caminho_readme}")
    novo_bloco = f"{MARCADOR_INICIO}\n{conteudo}\n{MARCADOR_FIM}"
    caminho_readme.write_text(padrao.sub(lambda _: novo_bloco, texto), encoding="utf-8")


def gerar_grafico(silver: dict[str, pd.DataFrame], destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    dolar = silver["dolar"]
    selic = silver["selic_meta"]

    fig, eixo_dolar = plt.subplots(figsize=(10, 4.5), dpi=120)
    eixo_dolar.plot(pd.to_datetime(dolar["data"]), dolar["valor"], color="#2563eb", linewidth=1.2, label="Dólar (R$)")
    eixo_dolar.set_ylabel("Dólar (R$)", color="#2563eb")
    eixo_dolar.tick_params(axis="y", labelcolor="#2563eb")

    eixo_selic = eixo_dolar.twinx()
    eixo_selic.step(pd.to_datetime(selic["data"]), selic["valor"], where="post", color="#d97706", linewidth=1.4, label="Selic meta (% a.a.)")
    eixo_selic.set_ylabel("Selic meta (% a.a.)", color="#d97706")
    eixo_selic.tick_params(axis="y", labelcolor="#d97706")

    for eixo in (eixo_dolar, eixo_selic):
        eixo.spines["top"].set_visible(False)
    eixo_dolar.grid(axis="y", alpha=0.25)
    eixo_dolar.set_title("Dólar (venda) e meta da Selic — fonte: Banco Central do Brasil (SGS)", fontsize=11)
    fig.tight_layout()
    fig.savefig(destino)
    plt.close(fig)
    return destino
