"""Consulta somente para leitura e integração dos modelos das sprints anteriores."""
from __future__ import annotations

import math
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

RAIZ = Path(__file__).resolve().parent
SENSORES = ["rotacao_rpm", "vibracao_mm_s", "temperatura_c", "corrente_a"]


def conectar():
    return sqlite3.connect((RAIZ / "motor.db").as_uri() + "?mode=ro", uri=True)


def listar_motores():
    with closing(conectar()) as banco:
        banco.row_factory = sqlite3.Row
        return [dict(r) for r in banco.execute("SELECT * FROM motores ORDER BY motor_id")]


def normalizar_periodo(inicio=None, fim=None):
    valores = []
    for texto in (inicio, fim):
        if not texto:
            valores.append(None)
            continue
        try:
            data = datetime.fromisoformat(str(texto))
        except ValueError as erro:
            raise ValueError("Informe um período válido no formato de data e hora.") from erro
        if data.tzinfo:
            raise ValueError("Use o horário da base, sem fuso horário.")
        valores.append(data)
    a, b = valores
    if b and len(str(fim)) == 10:
        b += timedelta(days=1, microseconds=-1)
    if a and b and a > b:
        raise ValueError("O início do período deve ser anterior ao fim.")
    return a.isoformat(sep=" ") if a else None, b.isoformat(sep=" ") if b else None


@lru_cache(maxsize=1)
def resultados():
    tabela = pd.read_csv(RAIZ / "dados_resultado/anomalias_leituras.csv", parse_dates=["timestamp"])
    return tabela


@lru_cache(maxsize=1)
def carregar_modelos():
    # A importação resolve as classes necessárias ao modelo serializado recebido.
    import deteccao_anomalias  # noqa: F401
    return joblib.load(RAIZ / "modelo_falhas.joblib"), joblib.load(RAIZ / "modelo_anomalias.joblib")


def analisar_leitura(motor_id, sensores):
    from manutencao_modelo import CLASS_NAMES
    from deteccao_anomalias import _nivel_severidade
    if set(sensores) != set(SENSORES):
        raise ValueError("Informe rotação, vibração, temperatura e corrente.")
    try:
        valores = {nome: float(sensores[nome]) for nome in SENSORES}
    except (ValueError, TypeError) as erro:
        raise ValueError("As leituras dos sensores devem ser números.") from erro
    if not all(math.isfinite(v) for v in valores.values()):
        raise ValueError("As leituras devem ser números finitos.")
    if any(valores[n] < 0 for n in ("rotacao_rpm", "vibracao_mm_s", "corrente_a")):
        raise ValueError("Rotação, vibração e corrente não podem ser negativas.")
    classificador, detector = carregar_modelos()
    entrada = pd.DataFrame([valores])
    probabilidades = classificador.predict_proba(entrada)[0]
    classes = classificador.classes_
    posicao = int(probabilidades.argmax())
    classe = int(classes[posicao])
    leitura = entrada.assign(motor_id=motor_id)
    score = float(detector.score_estatistico(leitura)[0])
    return {
        "classe_prevista": CLASS_NAMES[classe], "codigo_classe": classe,
        "probabilidade": round(float(probabilidades[posicao]), 6),
        "probabilidades": {CLASS_NAMES[int(c)]: round(float(p), 6) for c, p in zip(classes, probabilidades)},
        "score_anomalia": round(score, 6),
        "limiar": float(detector.limiar_estatistico),
        "anomalia": bool(score >= detector.limiar_estatistico),
        "score_isolation_forest": float(detector.score_isolation_forest(leitura)[0]),
        "severidade": _nivel_severidade(score, detector.limiar_estatistico),
        "referencia": "por motor" if motor_id in detector.perfil.medias_por_motor.index else "global",
        "leituras": valores,
    }


def consultar_contexto(motor_id=None, inicio=None, fim=None):
    inicio, fim = normalizar_periodo(inicio, fim)
    if motor_id is not None:
        if isinstance(motor_id, bool) or not str(motor_id).isdigit():
            raise ValueError("O identificador do motor deve ser um inteiro positivo.")
        motor_id = int(motor_id)
    with closing(conectar()) as banco:
        banco.row_factory = sqlite3.Row
        if motor_id is not None:
            registro = banco.execute("SELECT * FROM motores WHERE motor_id=?", (motor_id,)).fetchone()
            if not registro:
                return {"disponivel": False, "motivo": "Motor não cadastrado.", "motor_id": motor_id}
            motor = dict(registro)
        else:
            motor = None
        condicoes, parametros = [], []
        for sql, valor in [("motor_id=?", motor_id), ("timestamp>=?", inicio), ("timestamp<=?", fim)]:
            if valor is not None:
                condicoes.append(sql)
                parametros.append(valor)
        clausula = " WHERE " + " AND ".join(condicoes) if condicoes else ""
        leituras = pd.read_sql_query("SELECT * FROM leituras" + clausula + " ORDER BY motor_id,timestamp", banco, params=parametros)
    if leituras.empty:
        return {"disponivel": False, "motivo": "Não há leituras no período solicitado.", "motor": motor, "inicio": inicio, "fim": fim}
    tabela = resultados()
    mascara = pd.Series(True, index=tabela.index)
    if motor_id is not None:
        mascara &= tabela.motor_id.eq(motor_id)
    if inicio:
        mascara &= tabela.timestamp.ge(pd.Timestamp(inicio))
    if fim:
        mascara &= tabela.timestamp.le(pd.Timestamp(fim))
    scores = tabela.loc[mascara]
    ultima = leituras.sort_values("timestamp").iloc[-1]
    resumo = {
        "disponivel": True, "origem": "motor.db e dados_resultado/anomalias_leituras.csv",
        "dados_sinteticos": True, "motor": motor, "motor_id": motor_id,
        "inicio": str(leituras.timestamp.min()), "fim": str(leituras.timestamp.max()),
        "quantidade_leituras": len(leituras), "motores": int(leituras.motor_id.nunique()),
        "rotulos_historicos": {str(int(k)): int(v) for k, v in leituras.falha.value_counts().sort_index().items()},
        "sensores": {n: {"minimo": float(leituras[n].min()), "media": float(leituras[n].mean()), "maximo": float(leituras[n].max())} for n in SENSORES},
        "anomalias_baseline": int(scores.anomalia_estatistica.sum()),
        "anomalias_isolation_forest": int(scores.anomalia_isolation_forest.sum()),
        "anomalias_unicas": int(((scores.anomalia_estatistica == 1) | (scores.anomalia_isolation_forest == 1)).sum()),
        "anomalias_ambos_detectores": int(((scores.anomalia_estatistica == 1) & (scores.anomalia_isolation_forest == 1)).sum()),
        "score_maximo": float(scores.score_estatistico.max()),
        "historico_manutencao_disponivel": False,
        "serie": [{"instante": str(r.timestamp), "score": round(float(r.score_estatistico), 3), "anomalia": int(r.anomalia_estatistica)} for r in scores.iloc[::max(1, len(scores)//80)].itertuples()],
    }
    if motor_id is not None:
        resumo["ultima_leitura"] = {"instante": str(ultima.timestamp), **analisar_leitura(motor_id, {n: ultima[n] for n in SENSORES})}
    return resumo
