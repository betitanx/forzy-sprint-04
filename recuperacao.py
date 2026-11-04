"""Recuperação documental local com TF-IDF, metadados e fontes rastreáveis."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

RAIZ = Path(__file__).resolve().parent
PALAVRAS_COMUNS = "a o as os de da do das dos e em um uma para por com no na nos nas que qual quais como ao aos ou se ser sobre esse essa este esta meu minha".split()


def fragmentar(texto, tamanho=180, sobreposicao=30):
    palavras = texto.split()
    return [" ".join(palavras[i:i+tamanho]) for i in range(0, len(palavras), tamanho-sobreposicao) if palavras[i:i+tamanho]]


class IndiceDocumental:
    def __init__(self, pasta=None):
        self.pasta = Path(pasta or RAIZ / "base_documental")
        manifesto = self.pasta / "manifesto.json"
        metadados = json.loads(manifesto.read_text(encoding="utf-8")) if manifesto.exists() else {}
        self.fragmentos = []
        for arquivo in sorted(self.pasta.iterdir()):
            if arquivo.suffix.lower() not in {".md", ".txt", ".pdf"}:
                continue
            meta = metadados.get(arquivo.name, {})
            if arquivo.suffix.lower() == ".pdf":
                paginas = [(i+1, pagina.extract_text() or "") for i, pagina in enumerate(PdfReader(arquivo).pages)]
            else:
                paginas = [(None, arquivo.read_text(encoding="utf-8-sig"))]
            resumo_hash = hashlib.sha256(arquivo.read_bytes()).hexdigest()
            for pagina, texto in paginas:
                for numero, trecho in enumerate(fragmentar(texto)):
                    identificador = hashlib.sha256(f"{arquivo.name}:{pagina}:{numero}:{resumo_hash}".encode()).hexdigest()[:12]
                    self.fragmentos.append({"id": identificador, "arquivo": arquivo.name, "titulo": meta.get("titulo", arquivo.stem), "pagina": pagina, "trecho": trecho, "sha256": resumo_hash, "motores": meta.get("motores", []), "inicio": meta.get("inicio"), "fim": meta.get("fim"), "origem": meta.get("origem", "Documento local")})
        if not self.fragmentos:
            raise ValueError("A base documental não contém documentos legíveis.")
        self.vetorizador = TfidfVectorizer(strip_accents="unicode", lowercase=True, ngram_range=(1, 2), stop_words=PALAVRAS_COMUNS, sublinear_tf=True)
        self.matriz = self.vetorizador.fit_transform(f["trecho"] for f in self.fragmentos)

    def buscar(self, consulta, motor_id=None, inicio=None, fim=None, limite=5):
        if not isinstance(consulta, str) or not consulta.strip():
            return []
        vetor = self.vetorizador.transform([consulta])
        pontuacoes = cosine_similarity(vetor, self.matriz).ravel()
        encontrados = []
        for indice in pontuacoes.argsort()[::-1]:
            f = self.fragmentos[int(indice)]
            if pontuacoes[indice] < 0.035:
                continue
            if f["motores"] and (motor_id is None or motor_id not in f["motores"]):
                continue
            if inicio and f["fim"] and f["fim"] < str(inicio)[:10]:
                continue
            if fim and f["inicio"] and f["inicio"] > str(fim)[:10]:
                continue
            encontrados.append({**f, "similaridade": round(float(pontuacoes[indice]), 5)})
            if len(encontrados) >= limite:
                break
        return encontrados

    def inventario(self):
        return {"documentos": len({f["arquivo"] for f in self.fragmentos}), "fragmentos": len(self.fragmentos), "metodo": "TF-IDF e similaridade de cosseno", "dimensoes": self.matriz.shape[1]}

    def salvar_manifesto_indice(self, destino):
        Path(destino).write_text(json.dumps({"inventario": self.inventario(), "fragmentos": self.fragmentos}, ensure_ascii=False, indent=2), encoding="utf-8")
