"""Servidor local da demonstração Forzy."""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from assistente import indice_documental, responder
from operacao import listar_motores

RAIZ = Path(__file__).resolve().parent
ARQUIVOS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/estilo.css": ("estilo.css", "text/css")}


class Rotas(BaseHTTPRequestHandler):
    def enviar(self, codigo, conteudo, tipo="application/json"):
        dados = json.dumps(conteudo, ensure_ascii=False).encode() if tipo == "application/json" else conteudo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        rota = urlsplit(self.path).path
        if rota in ARQUIVOS:
            arquivo, tipo = ARQUIVOS[rota]
            self.enviar(200, (RAIZ / "web" / arquivo).read_bytes(), tipo)
        elif rota == "/api/status":
            self.enviar(200, {"chave_configurada": bool(os.getenv("OPENAI_API_KEY")), "modelo": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), "indice": indice_documental().inventario(), "dados_sinteticos": True})
        elif rota == "/api/motores":
            self.enviar(200, listar_motores())
        elif rota == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.enviar(404, {"erro": "Recurso não encontrado."})

    def do_POST(self):
        if self.path != "/api/chat":
            self.enviar(404, {"erro": "Recurso não encontrado."})
            return
        origem = self.headers.get("Origin")
        host = self.headers.get("Host")
        if origem and origem not in {f"http://{host}", f"https://{host}"}:
            self.enviar(403, {"erro": "Origem não permitida."})
            return
        try:
            tamanho = int(self.headers.get("Content-Length", "0"))
            if tamanho < 1 or tamanho > 32768:
                raise ValueError("A solicitação deve ter até 32 KB.")
            dados = json.loads(self.rfile.read(tamanho))
            if not isinstance(dados, dict):
                raise ValueError("Solicitação inválida.")
            permitido = {k: dados[k] for k in ("pergunta", "motor_id", "inicio", "fim", "sensores", "historico") if k in dados}
            resposta = responder(**permitido)
            self.enviar(200, resposta)
        except (ValueError, TypeError) as erro:
            self.enviar(400, {"erro": str(erro) if isinstance(erro, ValueError) else "Confira os campos da solicitação."})
        except RuntimeError as erro:
            self.enviar(502, {"erro": str(erro)})
        except Exception:
            self.enviar(500, {"erro": "Não foi possível concluir a consulta. Verifique o ambiente local."})

    def log_message(self, formato, *argumentos):
        # Registra somente rota e status, sem perguntas, respostas ou credenciais.
        print(formato % argumentos, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assistente local Forzy")
    parser.add_argument("--porta", type=int, default=8501)
    argumentos = parser.parse_args()
    servidor = ThreadingHTTPServer(("127.0.0.1", argumentos.porta), Rotas)
    print(f"Forzy disponível em http://127.0.0.1:{argumentos.porta}", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        servidor.server_close()
