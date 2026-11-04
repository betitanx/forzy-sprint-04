from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "motor.db"
MODEL_PATH = ROOT / "modelo_anomalias.joblib"
METRICS_PATH = ROOT / "metricas_anomalias.json"
RESULTS_PATH = ROOT / "dados_resultado" / "anomalias_leituras.csv"
RANKING_PATH = ROOT / "dados_resultado" / "ranking_motores_anomalias.csv"

FEATURES = ["rotacao_rpm", "vibracao_mm_s", "temperatura_c", "corrente_a"]
SENSOR_NAMES = {
    "rotacao_rpm": "rotação",
    "vibracao_mm_s": "vibração",
    "temperatura_c": "temperatura",
    "corrente_a": "corrente",
}
CLASS_NAMES = {
    0: "Normal",
    1: "Desbalanceamento",
    2: "Superaquecimento",
    3: "Falha mecânica",
}


def load_data(db_path: str | Path = DB_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega as tabelas históricas do banco SQLite."""
    connection = sqlite3.connect(db_path)
    try:
        leituras = pd.read_sql_query(
            "SELECT * FROM leituras",
            connection,
            parse_dates=["timestamp"],
        )
        motores = pd.read_sql_query("SELECT * FROM motores", connection)
        tipos_falha = pd.read_sql_query("SELECT * FROM tipos_falha", connection)
    finally:
        connection.close()

    leituras = leituras.sort_values(["motor_id", "timestamp"]).reset_index(drop=True)
    return leituras, motores, tipos_falha


def split_temporal_por_motor(
    leituras: pd.DataFrame,
    proporcao_treino: float = 0.56,
    proporcao_validacao: float = 0.14,
) -> pd.DataFrame:
    """Marca treino, validação e teste em ordem cronológica para cada motor."""
    if not 0 < proporcao_treino < 1:
        raise ValueError("A proporção de treino deve estar entre 0 e 1.")
    if not 0 <= proporcao_validacao < 1 - proporcao_treino:
        raise ValueError("A proporção de validação deve deixar dados para teste.")

    partes: list[pd.DataFrame] = []
    for _, grupo in leituras.sort_values(["motor_id", "timestamp"]).groupby("motor_id", sort=True):
        grupo = grupo.copy()
        corte_treino = int(len(grupo) * proporcao_treino)
        corte_validacao = int(len(grupo) * (proporcao_treino + proporcao_validacao))
        grupo["particao"] = "teste"
        grupo.iloc[:corte_treino, grupo.columns.get_loc("particao")] = "treino"
        grupo.iloc[corte_treino:corte_validacao, grupo.columns.get_loc("particao")] = "validacao"
        partes.append(grupo)

    return pd.concat(partes, ignore_index=True)


class PerfilNormal:
    """Mantém médias e desvios normais específicos de cada motor."""

    def __init__(self) -> None:
        self.medias_por_motor: pd.DataFrame | None = None
        self.desvios_por_motor: pd.DataFrame | None = None
        self.media_global: pd.Series | None = None
        self.desvio_global: pd.Series | None = None

    def fit(self, leituras_normais: pd.DataFrame) -> "PerfilNormal":
        if leituras_normais.empty:
            raise ValueError("Não há leituras normais suficientes para criar o perfil.")

        self.medias_por_motor = leituras_normais.groupby("motor_id")[FEATURES].mean()
        self.desvios_por_motor = leituras_normais.groupby("motor_id")[FEATURES].std()
        self.media_global = leituras_normais[FEATURES].mean()
        self.desvio_global = leituras_normais[FEATURES].std().replace(0, np.nan)
        self.desvio_global = self.desvio_global.fillna(1.0)
        self.desvios_por_motor = self.desvios_por_motor.fillna(self.desvio_global)
        self.desvios_por_motor = self.desvios_por_motor.replace(0, self.desvio_global)
        return self

    def referencia(self, motor_id: int | None) -> tuple[pd.Series, pd.Series]:
        if self.media_global is None or self.desvio_global is None:
            raise RuntimeError("O perfil normal ainda não foi treinado.")
        if (
            motor_id is not None
            and self.medias_por_motor is not None
            and motor_id in self.medias_por_motor.index
        ):
            return (
                self.medias_por_motor.loc[motor_id],
                self.desvios_por_motor.loc[motor_id],
            )
        return self.media_global, self.desvio_global

    def transform(self, leituras: pd.DataFrame) -> np.ndarray:
        """Converte sensores em desvios assinados e absolutos do perfil normal."""
        valores = leituras[FEATURES].to_numpy(dtype=float)
        desvios = []
        for motor_id, linha in zip(leituras["motor_id"], valores):
            media, desvio = self.referencia(int(motor_id) if pd.notna(motor_id) else None)
            z = (linha - media.to_numpy(dtype=float)) / np.maximum(desvio.to_numpy(dtype=float), 1e-6)
            desvios.append(np.concatenate([z, np.abs(z)]))
        return np.asarray(desvios, dtype=float)

    def desvios_por_sensor(self, leituras: pd.DataFrame) -> pd.DataFrame:
        matriz = self.transform(leituras)[:, len(FEATURES) :]
        return pd.DataFrame(
            matriz,
            columns=[f"{feature}_abs_z" for feature in FEATURES],
            index=leituras.index,
        )


def _selecionar_limiar(y_true: np.ndarray, scores: np.ndarray) -> tuple[float, dict[str, float]]:
    """Escolhe o limiar que maximiza F1 na validação temporal."""
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    if len(thresholds) == 0:
        return 0.0, {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    f1 = 2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    indice = int(np.nanargmax(f1))
    return float(thresholds[indice]), {
        "precision": float(precision[indice]),
        "recall": float(recall[indice]),
        "f1": float(f1[indice]),
    }


class DetectorAnomalias:
    """Detector semissupervisionado com baseline estatístico e Isolation Forest."""

    def __init__(
        self,
        n_estimators: int = 400,
        random_state: int = 42,
    ) -> None:
        self.perfil = PerfilNormal()
        self.normalizador = StandardScaler()
        self.modelo = IsolationForest(
            n_estimators=n_estimators,
            contamination="auto",
            random_state=random_state,
            n_jobs=-1,
        )
        self.limiar_estatistico: float | None = None
        self.limiar_isolation_forest: float | None = None
        self.parametros = {
            "n_estimators": n_estimators,
            "contamination": "auto",
            "random_state": random_state,
        }

    def fit(self, treino: pd.DataFrame) -> "DetectorAnomalias":
        normais = treino.loc[treino["falha"] == 0].copy()
        self.perfil.fit(normais)
        caracteristicas = self.perfil.transform(normais)
        caracteristicas_normalizadas = self.normalizador.fit_transform(caracteristicas)
        self.modelo.fit(caracteristicas_normalizadas)
        return self

    def score_estatistico(self, leituras: pd.DataFrame) -> np.ndarray:
        desvios = self.perfil.transform(leituras)[:, len(FEATURES) :]
        return np.sqrt(np.mean(desvios**2, axis=1))

    def score_isolation_forest(self, leituras: pd.DataFrame) -> np.ndarray:
        caracteristicas = self.perfil.transform(leituras)
        normalizadas = self.normalizador.transform(caracteristicas)
        return -self.modelo.decision_function(normalizadas)

    def calibrar(self, validacao: pd.DataFrame) -> dict[str, Any]:
        y_true = (validacao["falha"].to_numpy() > 0).astype(int)
        score_estatistico = self.score_estatistico(validacao)
        score_isolation = self.score_isolation_forest(validacao)
        self.limiar_estatistico, resultado_estatistico = _selecionar_limiar(
            y_true, score_estatistico
        )
        self.limiar_isolation_forest, resultado_isolation = _selecionar_limiar(
            y_true, score_isolation
        )
        return {
            "baseline_estatistico": resultado_estatistico,
            "isolation_forest": resultado_isolation,
            "limiar_estatistico": self.limiar_estatistico,
            "limiar_isolation_forest": self.limiar_isolation_forest,
        }

    def prever_estatistico(self, leituras: pd.DataFrame) -> np.ndarray:
        if self.limiar_estatistico is None:
            raise RuntimeError("O limiar estatístico ainda não foi calibrado.")
        return (self.score_estatistico(leituras) >= self.limiar_estatistico).astype(int)

    def prever_isolation_forest(self, leituras: pd.DataFrame) -> np.ndarray:
        if self.limiar_isolation_forest is None:
            raise RuntimeError("O limiar do Isolation Forest ainda não foi calibrado.")
        return (self.score_isolation_forest(leituras) >= self.limiar_isolation_forest).astype(int)


def _avaliar_scores(
    y_true: np.ndarray,
    scores: np.ndarray,
    limiar: float,
) -> dict[str, Any]:
    previsoes = (scores >= limiar).astype(int)
    relatorio = classification_report(
        y_true,
        previsoes,
        labels=[0, 1],
        target_names=["Normal", "Anomalia"],
        output_dict=True,
        zero_division=0,
    )
    return {
        "acuracia": float(accuracy_score(y_true, previsoes)),
        "precision_anomalia": float(relatorio["Anomalia"]["precision"]),
        "recall_anomalia": float(relatorio["Anomalia"]["recall"]),
        "f1_anomalia": float(relatorio["Anomalia"]["f1-score"]),
        "f1_macro": float(relatorio["macro avg"]["f1-score"]),
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "matriz_confusao": confusion_matrix(y_true, previsoes, labels=[0, 1]).tolist(),
        "limiar": float(limiar),
        "quantidade_anomalias": int(previsoes.sum()),
        "taxa_anomalias": float(previsoes.mean()),
    }


def _rotulo_sensores(desvios: pd.Series, quantidade: int = 2) -> str:
    ordenados = desvios.sort_values(ascending=False).head(quantidade)
    return ", ".join(SENSOR_NAMES[col.replace("_abs_z", "")] for col in ordenados.index)


def _nivel_severidade(score: float, limiar: float) -> str:
    if score >= limiar * 1.5:
        return "crítico"
    if score >= limiar:
        return "alto"
    if score >= limiar * 0.75:
        return "atenção"
    return "baixo"


def construir_tabela_resultados(
    leituras: pd.DataFrame,
    detector: DetectorAnomalias,
) -> pd.DataFrame:
    resultados = leituras.copy()
    resultados["score_estatistico"] = detector.score_estatistico(leituras)
    resultados["score_isolation_forest"] = detector.score_isolation_forest(leituras)
    resultados["anomalia_estatistica"] = detector.prever_estatistico(leituras)
    resultados["anomalia_isolation_forest"] = detector.prever_isolation_forest(leituras)
    desvios = detector.perfil.desvios_por_sensor(leituras)
    resultados["maior_desvio_z"] = desvios.max(axis=1).to_numpy()
    resultados["sensores_contribuintes"] = [
        _rotulo_sensores(linha) for _, linha in desvios.iterrows()
    ]
    resultados["severidade_operacional"] = [
        _nivel_severidade(score, detector.limiar_estatistico)
        for score in resultados["score_estatistico"]
    ]
    resultados = resultados.sort_values(["motor_id", "timestamp"]).reset_index(drop=True)
    grupo_motor = resultados.groupby("motor_id", sort=False)
    resultados["score_medio_movel_5"] = grupo_motor["score_estatistico"].transform(
        lambda serie: serie.rolling(window=5, min_periods=1).mean()
    )
    resultados["score_maximo_movel_5"] = grupo_motor["score_estatistico"].transform(
        lambda serie: serie.rolling(window=5, min_periods=1).max()
    )
    resultados["alertas_ultimas_5"] = grupo_motor["anomalia_estatistica"].transform(
        lambda serie: serie.rolling(window=5, min_periods=1).sum()
    )
    resultados["anomalia_persistente_5"] = (resultados["alertas_ultimas_5"] >= 2).astype(int)
    return resultados


def _ranking_motores(resultados: pd.DataFrame) -> pd.DataFrame:
    ranking = (
        resultados.groupby("motor_id")
        .agg(
            leituras=("motor_id", "size"),
            anomalias_estatisticas=("anomalia_estatistica", "sum"),
            anomalias_isolation_forest=("anomalia_isolation_forest", "sum"),
            periodos_persistentes_5=("anomalia_persistente_5", "sum"),
            score_medio=("score_estatistico", "mean"),
            score_maximo=("score_estatistico", "max"),
            falhas_rotuladas=("falha", lambda serie: int((serie > 0).sum())),
        )
        .reset_index()
    )
    ranking["taxa_anomalias"] = ranking["anomalias_estatisticas"] / ranking["leituras"]
    return ranking.sort_values(
        ["anomalias_estatisticas", "score_medio"], ascending=False
    ).reset_index(drop=True)


def train_and_evaluate(
    db_path: str | Path = DB_PATH,
    model_path: str | Path = MODEL_PATH,
    metrics_path: str | Path = METRICS_PATH,
    results_path: str | Path = RESULTS_PATH,
    ranking_path: str | Path = RANKING_PATH,
) -> dict[str, Any]:
    """Treina, calibra, avalia e persiste o detector de anomalias."""
    leituras, motores, tipos_falha = load_data(db_path)
    particionado = split_temporal_por_motor(leituras)
    treino = particionado[particionado["particao"] == "treino"]
    validacao = particionado[particionado["particao"] == "validacao"]
    teste = particionado[particionado["particao"] == "teste"]

    detector = DetectorAnomalias()
    detector.fit(treino)
    calibracao = detector.calibrar(validacao)

    y_teste = (teste["falha"].to_numpy() > 0).astype(int)
    metricas_teste = {
        "baseline_estatistico": _avaliar_scores(
            y_teste,
            detector.score_estatistico(teste),
            detector.limiar_estatistico,
        ),
        "isolation_forest": _avaliar_scores(
            y_teste,
            detector.score_isolation_forest(teste),
            detector.limiar_isolation_forest,
        ),
    }

    resultados = construir_tabela_resultados(particionado, detector)
    ranking = _ranking_motores(resultados)
    modelo_path = Path(model_path)
    metricas_path = Path(metrics_path)
    resultados_path = Path(results_path)
    ranking_path = Path(ranking_path)
    modelo_path.parent.mkdir(parents=True, exist_ok=True)
    metricas_path.parent.mkdir(parents=True, exist_ok=True)
    resultados_path.parent.mkdir(parents=True, exist_ok=True)
    ranking_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(detector, modelo_path)
    resultados.to_csv(resultados_path, index=False, encoding="utf-8-sig")
    ranking.to_csv(ranking_path, index=False, encoding="utf-8-sig")

    anomalias_teste = resultados[
        (resultados["particao"] == "teste") & (resultados["anomalia_estatistica"] == 1)
    ]
    contagem_sensores = (
        anomalias_teste["sensores_contribuintes"]
        .str.split(", ")
        .explode()
        .value_counts()
        .to_dict()
    )
    metricas = {
        "origem": "motor.db, base histórica disponibilizada para a Sprint 3",
        "linhas": int(len(leituras)),
        "motores": int(leituras["motor_id"].nunique()),
        "frequencia": "uma leitura por minuto",
        "periodo": {
            "inicio": str(leituras["timestamp"].min()),
            "fim": str(leituras["timestamp"].max()),
        },
        "variaveis_sensores": FEATURES,
        "estrategia": "semissupervisionada: treino somente com leituras falha=0; rótulos usados na avaliação",
        "particoes": particionado["particao"].value_counts().to_dict(),
        "modelo": detector.parametros,
        "calibracao_validacao": calibracao,
        "metricas_teste": metricas_teste,
        "modelo_operacional": "baseline_estatistico_por_motor",
        "janela_temporal": {
            "tamanho": 5,
            "medidas": [
                "score_medio_movel_5",
                "score_maximo_movel_5",
                "alertas_ultimas_5",
                "anomalia_persistente_5",
            ],
        },
        "sensores_mais_frequentes_nos_alertas": {
            str(chave): int(valor) for chave, valor in contagem_sensores.items()
        },
        "top_motores_por_anomalias": ranking.head(10).to_dict(orient="records"),
        "tipos_falha": tipos_falha.to_dict(orient="records"),
        "cadastro_motores_linhas": int(len(motores)),
    }
    metricas_path.write_text(
        json.dumps(metricas, indent=2, ensure_ascii=False, default=float),
        encoding="utf-8",
    )
    return {
        "detector": detector,
        "metricas": metricas,
        "resultados": resultados,
        "ranking": ranking,
    }


def prever_anomalia_motor(
    motor_id: int | None,
    rotacao_rpm: float,
    vibracao_mm_s: float,
    temperatura_c: float,
    corrente_a: float,
    model_path: str | Path = MODEL_PATH,
) -> dict[str, Any]:
    """Calcula o score operacional para uma leitura recebida pelo agente."""
    detector: DetectorAnomalias = joblib.load(model_path)
    leitura = pd.DataFrame(
        [
            {
                "motor_id": motor_id,
                "rotacao_rpm": rotacao_rpm,
                "vibracao_mm_s": vibracao_mm_s,
                "temperatura_c": temperatura_c,
                "corrente_a": corrente_a,
            }
        ]
    )
    score_estatistico = float(detector.score_estatistico(leitura)[0])
    score_isolation = float(detector.score_isolation_forest(leitura)[0])
    desvios = detector.perfil.desvios_por_sensor(leitura).iloc[0]
    media, desvio = detector.perfil.referencia(motor_id)
    anomalia = bool(score_estatistico >= detector.limiar_estatistico)
    return {
        "motor_id": motor_id,
        "anomalia": anomalia,
        "score_anomalia": round(score_estatistico, 4),
        "score_isolation_forest": round(score_isolation, 4),
        "limiar_operacional": round(float(detector.limiar_estatistico), 4),
        "severidade": _nivel_severidade(score_estatistico, detector.limiar_estatistico),
        "sensores_responsaveis": _rotulo_sensores(desvios, quantidade=4),
        "desvios_absolutos_z": {
            SENSOR_NAMES[feature]: round(float(desvios[f"{feature}_abs_z"]), 3)
            for feature in FEATURES
        },
        "referencia_normal": {
            SENSOR_NAMES[feature]: {
                "media": round(float(media[feature]), 3),
                "desvio": round(float(desvio[feature]), 3),
            }
            for feature in FEATURES
        },
        "leituras": {
            "rotacao_rpm": rotacao_rpm,
            "vibracao_mm_s": vibracao_mm_s,
            "temperatura_c": temperatura_c,
            "corrente_a": corrente_a,
        },
    }


def main() -> None:
    resultado = train_and_evaluate()
    metricas = resultado["metricas"]["metricas_teste"]
    print("Modelo de anomalias treinado.")
    for nome, valores in metricas.items():
        print(
            f"{nome}: F1={valores['f1_anomalia']:.4f}, "
            f"recall={valores['recall_anomalia']:.4f}, "
            f"PR-AUC={valores['pr_auc']:.4f}"
        )


if __name__ == "__main__":
    main()
