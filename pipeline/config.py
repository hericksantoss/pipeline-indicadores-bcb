"""Configuração central do pipeline: séries do Banco Central, caminhos e limites."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Serie:
    nome: str
    codigo: int  # código da série no SGS (Sistema Gerenciador de Séries Temporais) do BCB
    descricao: str
    unidade: str
    frequencia: str  # "diaria" ou "mensal"
    valor_min: float  # faixa de valores plausíveis, usada na checagem de qualidade
    valor_max: float


SERIES: dict[str, Serie] = {
    "dolar": Serie("dolar", 1, "Dólar americano (venda)", "R$", "diaria", 1.0, 20.0),
    "euro": Serie("euro", 21619, "Euro (venda)", "R$", "diaria", 1.0, 20.0),
    "selic_meta": Serie("selic_meta", 432, "Meta da taxa Selic (Copom)", "% a.a.", "diaria", 0.0, 50.0),
    "ipca": Serie("ipca", 433, "IPCA - variação mensal", "%", "mensal", -5.0, 10.0),
}

# Primeira carga busca a partir desta data. Depois disso, a carga é incremental.
DATA_INICIAL = date(2020, 1, 1)

# Na carga incremental, reprocessa alguns dias para trás para pegar correções do BCB.
JANELA_REPROCESSAMENTO_DIAS = 10

# A API do SGS limita consultas de séries diárias a janelas de até 10 anos.
# Usamos janelas menores por segurança.
JANELA_MAXIMA_CONSULTA_DIAS = 365 * 5

# Quantos dias sem dado novo são aceitáveis antes de a checagem de frescor falhar.
FRESCOR_MAXIMO_DIAS = {"diaria": 7, "mensal": 75}

RAIZ = Path(__file__).resolve().parent.parent
DIRETORIO_DADOS = RAIZ / "data"
README = RAIZ / "README.md"
