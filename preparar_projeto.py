"""Prepara os artefatos locais a partir do banco fornecido, sem chamar a API."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def preparar(raiz=RAIZ):
    raiz = Path(raiz)
    banco = raiz / "motor.db"
    if not banco.is_file():
        raise FileNotFoundError("O arquivo motor.db deve estar na pasta do projeto.")
    criados = []
    if not (raiz / "modelo_falhas.joblib").is_file():
        from manutencao_modelo import train_and_evaluate
        print("Treinando o classificador da Sprint 02...", flush=True)
        train_and_evaluate(db_path=banco, model_path=raiz / "modelo_falhas.joblib", metrics_path=raiz / "metricas_modelo.json")
        criados.append("classificador")
    if not all((raiz / nome).is_file() for nome in ("modelo_anomalias.joblib", "dados_resultado/anomalias_leituras.csv")):
        from deteccao_anomalias import train_and_evaluate
        print("Treinando os detectores e calculando os resultados da Sprint 03...", flush=True)
        train_and_evaluate(db_path=banco, model_path=raiz / "modelo_anomalias.joblib", metrics_path=raiz / "metricas_anomalias.json", results_path=raiz / "dados_resultado/anomalias_leituras.csv", ranking_path=raiz / "dados_resultado/ranking_motores_anomalias.csv")
        criados.append("detectores")
    print("Preparação concluída." if criados else "Os artefatos necessários já estão disponíveis.", flush=True)
    return criados


if __name__ == "__main__":
    preparar()
