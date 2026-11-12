"""Fixtures: uma API falsa do BCB, para os testes rodarem sem internet."""

from datetime import date, timedelta

import pytest

from pipeline.config import SERIES
from pipeline.report import MARCADOR_FIM, MARCADOR_INICIO


def _dias_uteis(inicio: date, fim: date):
    atual = inicio
    while atual <= fim:
        if atual.weekday() < 5:
            yield atual
        atual += timedelta(days=1)


def _primeiros_dias_do_mes(inicio: date, fim: date):
    atual = date(inicio.year, inicio.month, 1)
    while atual <= fim:
        yield atual
        atual = date(atual.year + (atual.month == 12), atual.month % 12 + 1, 1)


class ApiFalsa:
    """Imita o SGS: devolve {"data": "dd/mm/aaaa", "valor": "x.xx"} dentro do período pedido."""

    def __init__(self, ultimo_dia_com_dado: date, ultimo_mes_ipca: date):
        self.ultimo_dia = ultimo_dia_com_dado
        self.ultimo_mes_ipca = ultimo_mes_ipca
        self.chamadas: list[tuple[int, date, date]] = []

    def _valor(self, codigo: int, d: date) -> float:
        n = d.toordinal() - date(2020, 1, 1).toordinal()
        if codigo == SERIES["dolar"].codigo:
            return 4.0 + (n % 400) / 200
        if codigo == SERIES["euro"].codigo:
            return 4.5 + (n % 400) / 200
        if codigo == SERIES["selic_meta"].codigo:
            return 10.75 if d.year >= 2024 else 13.75
        if codigo == SERIES["ipca"].codigo:
            return 0.4
        raise KeyError(codigo)

    def __call__(self, codigo: int, inicio: date, fim: date) -> list[dict]:
        self.chamadas.append((codigo, inicio, fim))
        if codigo == SERIES["ipca"].codigo:
            datas = [d for d in _primeiros_dias_do_mes(inicio, fim) if d >= inicio and d <= self.ultimo_mes_ipca]
        else:
            datas = list(_dias_uteis(inicio, min(fim, self.ultimo_dia)))
        return [{"data": d.strftime("%d/%m/%Y"), "valor": f"{self._valor(codigo, d):.4f}"} for d in datas]


@pytest.fixture
def api_falsa():
    return ApiFalsa(ultimo_dia_com_dado=date(2026, 11, 11), ultimo_mes_ipca=date(2026, 9, 1))


@pytest.fixture
def readme(tmp_path):
    caminho = tmp_path / "README.md"
    caminho.write_text(f"# Teste\n\n{MARCADOR_INICIO}\nantigo\n{MARCADOR_FIM}\n\nrodapé\n", encoding="utf-8")
    return caminho
