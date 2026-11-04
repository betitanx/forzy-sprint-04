from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "motor.db"
MODEL_PATH = ROOT / "modelo_falhas.joblib"
METRICS_PATH = ROOT / "metricas_modelo.json"

FEATURES = ["rotacao_rpm", "vibracao_mm_s", "temperatura_c", "corrente_a"]
CLASS_NAMES = {
    0: "Normal",
    1: "Desbalanceamento",
    2: "Superaquecimento",
    3: "Falha mecânica",
}


def load_data(db_path: str | Path = DB_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega as tabelas principais do SQLite."""
    conn = sqlite3.connect(db_path)
    try:
        leituras = pd.read_sql_query("SELECT * FROM leituras", conn, parse_dates=["timestamp"])
        motores = pd.read_sql_query("SELECT * FROM motores", conn)
        tipos = pd.read_sql_query("SELECT * FROM tipos_falha", conn)
    finally:
        conn.close()

    leituras = leituras.sort_values(["motor_id", "timestamp"]).reset_index(drop=True)
    return leituras, motores, tipos


def chronological_split_by_motor(
    leituras: pd.DataFrame,
    train_fraction: float = 0.70,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide cada série de motor em passado para treino e futuro para teste."""
    parts_train: list[pd.DataFrame] = []
    parts_test: list[pd.DataFrame] = []

    for _, group in leituras.sort_values(["motor_id", "timestamp"]).groupby("motor_id", sort=True):
        cutoff = int(len(group) * train_fraction)
        parts_train.append(group.iloc[:cutoff])
        parts_test.append(group.iloc[cutoff:])

    return pd.concat(parts_train).reset_index(drop=True), pd.concat(parts_test).reset_index(drop=True)


def build_pipeline(random_state: int = 43) -> Pipeline:
    return Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                ExtraTreesClassifier(
                    n_estimators=500,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def train_and_evaluate(
    db_path: str | Path = DB_PATH,
    model_path: str | Path = MODEL_PATH,
    metrics_path: str | Path = METRICS_PATH,
) -> dict[str, Any]:
    leituras, _, _ = load_data(db_path)
    train_df, test_df = chronological_split_by_motor(leituras)

    model = build_pipeline()
    model.fit(train_df[FEATURES], train_df["falha"])

    y_true = test_df["falha"]
    y_pred = model.predict(test_df[FEATURES])
    labels = sorted(CLASS_NAMES)
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        target_names=[CLASS_NAMES[i] for i in labels],
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    metrics: dict[str, Any] = {
        "features": FEATURES,
        "classes": CLASS_NAMES,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "train_distribution": {str(k): int(v) for k, v in train_df["falha"].value_counts().sort_index().items()},
        "test_distribution": {str(k): int(v) for k, v in test_df["falha"].value_counts().sort_index().items()},
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
    }

    model_path = Path(model_path)
    metrics_path = Path(metrics_path)
    joblib.dump(model, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return metrics


def load_model(model_path: str | Path = MODEL_PATH) -> Pipeline:
    return joblib.load(model_path)


def interpretar_sinais(
    rotacao_rpm: float,
    vibracao_mm_s: float,
    temperatura_c: float,
    corrente_a: float,
) -> list[str]:
    sinais: list[str] = []
    if vibracao_mm_s >= 6.0:
        sinais.append("vibração elevada")
    elif vibracao_mm_s >= 4.0:
        sinais.append("vibração moderadamente alta")

    if temperatura_c >= 85.0:
        sinais.append("temperatura elevada")
    elif temperatura_c >= 78.0:
        sinais.append("temperatura acima do nominal")

    if corrente_a >= 14.5:
        sinais.append("corrente elevada")
    elif corrente_a >= 13.8:
        sinais.append("corrente acima do nominal")

    if rotacao_rpm <= 1650.0:
        sinais.append("queda de rotação")
    elif rotacao_rpm <= 1720.0:
        sinais.append("rotação abaixo do regime esperado")

    if not sinais:
        sinais.append("sensores dentro da faixa operacional usual")
    return sinais


def nivel_risco(probabilidade: float, classe: int) -> str:
    if classe == 0 and probabilidade >= 0.70:
        return "baixo"
    if probabilidade >= 0.75:
        return "alto"
    if probabilidade >= 0.50:
        return "moderado"
    return "incerto"


def prever_falha_motor(
    rotacao_rpm: float,
    vibracao_mm_s: float,
    temperatura_c: float,
    corrente_a: float,
    model_path: str | Path = MODEL_PATH,
) -> dict[str, Any]:
    model = load_model(model_path)
    entrada = pd.DataFrame(
        [[rotacao_rpm, vibracao_mm_s, temperatura_c, corrente_a]],
        columns=FEATURES,
    )
    pred = int(model.predict(entrada)[0])
    classes = [int(c) for c in model.named_steps["classifier"].classes_]
    proba = model.predict_proba(entrada)[0]
    probabilidades = {
        str(codigo): {
            "nome": CLASS_NAMES[codigo],
            "probabilidade": float(np.round(prob, 4)),
        }
        for codigo, prob in zip(classes, proba)
    }
    prob_pred = probabilidades[str(pred)]["probabilidade"]

    return {
        "classe_prevista": pred,
        "nome_classe": CLASS_NAMES[pred],
        "probabilidade": prob_pred,
        "nivel_risco": nivel_risco(prob_pred, pred),
        "probabilidades": probabilidades,
        "sinais_observados": interpretar_sinais(rotacao_rpm, vibracao_mm_s, temperatura_c, corrente_a),
        "leituras": {
            "rotacao_rpm": rotacao_rpm,
            "vibracao_mm_s": vibracao_mm_s,
            "temperatura_c": temperatura_c,
            "corrente_a": corrente_a,
        },
    }


if __name__ == "__main__":
    metrics = train_and_evaluate()
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
