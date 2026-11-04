"""Executa três consultas reais à API e registra respostas e verificações objetivas."""
import json
from datetime import datetime, timezone
from pathlib import Path

from assistente import responder

CENARIOS = [
    {"id": "01_anomalia", "pergunta": "O motor 3 apresentou anomalias no período selecionado? Informe a quantidade de leituras, o total de anomalias do baseline, o maior score e diferencie isso da classe prevista na última leitura.", "esperado": "Citar os totais corretos do recorte e separar rótulo, previsão e score."},
    {"id": "02_operacao_documentacao", "pergunta": "Relacione os dados operacionais do motor 3 com a documentação sobre superaquecimento e explique como investigar os desvios. Use fontes dos dados e dos documentos, sem inventar um manual de fabricante.", "esperado": "Combinar evidência operacional e documento recuperado, com fontes dos dois tipos e limites da análise."},
    {"id": "03_informacao_insuficiente", "pergunta": "Qual foi a última troca de rolamento do motor 3, em que data e qual técnico realizou o serviço?", "esperado": "Declarar que não há histórico de manutenção e não inventar data ou técnico."},
]


def executar():
    destino = Path(__file__).parent / "evidencias/cenarios.json"
    registros = []
    for cenario in CENARIOS:
        resposta = responder(cenario["pergunta"], motor_id=3, inicio="2026-01-01T17:30:00", fim="2026-01-02T00:59:00")
        fontes = resposta["fontes"]
        tipos = {f["tipo"] for f in fontes}
        verificacao = bool(fontes)
        if cenario["id"].startswith("02"):
            verificacao = {"operacional", "documento"}.issubset(tipos)
        if cenario["id"].startswith("03"):
            verificacao = resposta["informacao_insuficiente"]
        registros.append({**cenario, "executado_em_utc": datetime.now(timezone.utc).isoformat(), "filtros": {"motor_id": 3, "inicio": "2026-01-01T17:30:00", "fim": "2026-01-02T00:59:00"}, "verificacao_automatica": verificacao, "resultado": resposta})
        destino.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
        print(cenario["id"], "verificação:", verificacao, "resposta:", resposta["resposta"], flush=True)
    if not all(r["verificacao_automatica"] for r in registros):
        raise SystemExit("Há cenários que exigem revisão.")


if __name__ == "__main__":
    executar()
