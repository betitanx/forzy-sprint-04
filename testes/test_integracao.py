import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from assistente import gerar_resposta, preparar_contexto, responder
from operacao import analisar_leitura, consultar_contexto, normalizar_periodo
from recuperacao import IndiceDocumental


class Verificacoes(unittest.TestCase):
    def test_periodo_invertido_nao_e_consultado(self):
        with self.assertRaises(ValueError):
            normalizar_periodo("2026-01-02", "2026-01-01")

    def test_dia_final_inclui_todas_as_leituras(self):
        self.assertEqual(consultar_contexto(3, "2026-01-01", "2026-01-02")["quantidade_leituras"], 1500)

    def test_motor_inexistente_nao_usa_outro_motor(self):
        self.assertFalse(consultar_contexto(999)["disponivel"])

    def test_sem_dados_nao_usa_outro_periodo(self):
        self.assertFalse(consultar_contexto(3, "2030-01-01", "2030-01-02")["disponivel"])

    def test_total_nao_duplica_alertas_dos_detectores(self):
        contexto = consultar_contexto(3, "2026-01-01T17:30:00", "2026-01-02T00:59:00")
        self.assertEqual(contexto["anomalias_baseline"], 2)
        self.assertEqual(contexto["anomalias_isolation_forest"], 4)
        self.assertEqual(contexto["anomalias_unicas"], 4)
        self.assertEqual(contexto["anomalias_ambos_detectores"], 2)

    def test_ambiguidade_nao_chama_api(self):
        resposta = responder("Compare o motor 3 e o motor 4")
        self.assertEqual(resposta["tipo_geracao"], "Validação local")

    def test_motor_divergente_pede_esclarecimento(self):
        contexto, pergunta = preparar_contexto("Analise o motor 3", 4)
        self.assertIsNone(contexto)
        self.assertIn("Ajuste o filtro", pergunta)

    def test_leitura_nao_finita_e_rejeitada(self):
        with self.assertRaises(ValueError):
            analisar_leitura(3, {"rotacao_rpm": 1700, "vibracao_mm_s": float("nan"), "temperatura_c": 90, "corrente_a": 14})

    def test_recuperacao_restringe_motor_e_vigencia(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            (raiz / "a.md").write_text("Procedimento especial de vibração e temperatura.", encoding="utf-8")
            (raiz / "b.md").write_text("Documentação geral da temperatura.", encoding="utf-8")
            (raiz / "manifesto.json").write_text(json.dumps({"a.md": {"motores": [3], "inicio": "2026-01-01", "fim": "2026-12-31"}}), encoding="utf-8")
            indice = IndiceDocumental(raiz)
            self.assertIn("a.md", [f["arquivo"] for f in indice.buscar("vibração temperatura", 3, "2026-01-01", "2026-01-02")])
            self.assertNotIn("a.md", [f["arquivo"] for f in indice.buscar("vibração temperatura", 4)])
            self.assertNotIn("a.md", [f["arquivo"] for f in indice.buscar("vibração temperatura", 3, "2030-01-01")])

    def test_consulta_sem_vocabulario_nao_inventa_trecho(self):
        self.assertEqual(IndiceDocumental().buscar("xyzxyzquasarzzzz"), [])

    def test_referencia_inexistente_e_rejeitada(self):
        resposta_falsa = SimpleNamespace(output_text=json.dumps({"resposta": "Texto [F99]", "fontes": ["F99"], "informacao_insuficiente": False}),model="teste",usage=None)
        cliente = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: resposta_falsa))
        with self.assertRaises(RuntimeError):
            gerar_resposta({"fontes": [], "serie": [], "operacao": {}}, cliente)

    def test_referencia_inexistente_agrupada_e_rejeitada(self):
        resposta_falsa = SimpleNamespace(output_text=json.dumps({"resposta": "Resultado [O1, F99]", "fontes": ["O1"], "informacao_insuficiente": False}), model="teste", usage=None)
        cliente = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: resposta_falsa))
        with self.assertRaises(RuntimeError):
            gerar_resposta({"fontes": [{"id": "O1"}], "serie": [], "operacao": {}}, cliente)


if __name__ == "__main__":
    unittest.main()
