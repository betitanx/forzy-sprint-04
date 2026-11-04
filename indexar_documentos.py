import json
from pathlib import Path
from recuperacao import IndiceDocumental

if __name__ == "__main__":
    indice = IndiceDocumental()
    destino = Path(__file__).parent / "evidencias/indice_documental.json"
    destino.parent.mkdir(exist_ok=True)
    indice.salvar_manifesto_indice(destino)
    print(json.dumps(indice.inventario(), ensure_ascii=False))
