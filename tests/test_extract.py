from datetime import date

import pytest
import requests

from pipeline.extract import ErroExtracao, _janelas, buscar_serie


class RespostaFalsa:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._corpo


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def get(self, url, params, timeout):
        self.chamadas.append((url, params))
        return self.respostas.pop(0)


def test_janelas_cobrem_o_periodo_sem_buraco():
    janelas = _janelas(date(2020, 1, 1), date(2020, 1, 25), 10)
    assert janelas == [
        (date(2020, 1, 1), date(2020, 1, 10)),
        (date(2020, 1, 11), date(2020, 1, 20)),
        (date(2020, 1, 21), date(2020, 1, 25)),
    ]


def test_monta_parametros_no_formato_do_bcb():
    sessao = SessaoFalsa([RespostaFalsa(200, [{"data": "02/01/2025", "valor": "6.1"}])])
    dados = buscar_serie(1, date(2025, 1, 2), date(2025, 1, 3), sessao=sessao)
    url, params = sessao.chamadas[0]
    assert url.endswith("bcdata.sgs.1/dados")
    assert params == {"formato": "json", "dataInicial": "02/01/2025", "dataFinal": "03/01/2025"}
    assert dados == [{"data": "02/01/2025", "valor": "6.1"}]


def test_404_significa_periodo_sem_dados():
    sessao = SessaoFalsa([RespostaFalsa(404, {"erro": "Value(s) not found"})])
    assert buscar_serie(1, date(2025, 1, 1), date(2025, 1, 1), sessao=sessao) == []


def test_tenta_de_novo_e_desiste_depois_do_limite():
    sessao = SessaoFalsa([RespostaFalsa(503, None), RespostaFalsa(200, [])])
    assert buscar_serie(1, date(2025, 1, 2), date(2025, 1, 2), sessao=sessao, espera_base=0) == []
    assert len(sessao.chamadas) == 2

    sessao = SessaoFalsa([RespostaFalsa(503, None)] * 3)
    with pytest.raises(ErroExtracao):
        buscar_serie(1, date(2025, 1, 2), date(2025, 1, 2), sessao=sessao, tentativas=3, espera_base=0)
