# Especificação da Sprint 04

## Objetivo e escopo

Entregar um assistente local em português-BR que combine o classificador da Sprint 02, o detector da Sprint 03, o histórico sintético e documentos recuperados, com fontes verificáveis. A interface permitirá selecionar motor e período, fazer perguntas e inspecionar evidências. Não serão inventados registros de manutenção ou manuais de fabricante.

## Decisões

- Preservar os arquivos originais recebidos; integrar cópias nesta pasta.
- Manter Python e os modelos existentes. Usar servidor HTTP da biblioteca padrão e interface HTML/CSS/JavaScript sem processo de compilação.
- Fazer recuperação local com TF-IDF e similaridade de cosseno; usar OpenAI Responses para gerar respostas estruturadas com referências ao contexto. A chave fica apenas no servidor.
- Documentos em Markdown, texto e PDF, fragmentados com metadados de origem, página, motor e vigência. O corpus inicial documenta a base sintética e os modelos; não contém manuais de fabricante.
- Consultas ao banco serão parametrizadas e somente para leitura. Nenhuma pergunta produz ações físicas sobre equipamentos.

## Comandos

```powershell
python -m pip install -r requirements.txt
python indexar_documentos.py
python -m unittest discover -s testes -v
python avaliar_cenarios.py
python app.py
```

## Estrutura

- `operacao.py`: histórico, validação de filtros e integração dos modelos.
- `recuperacao.py`: indexação e busca documental.
- `assistente.py`: contexto, geração e referências.
- `app.py` e `web/`: servidor e interface.
- `testes/`: testes locais de filtros, recuperação e tratamento de erros.
- `evidencias/`: execuções dos cenários e capturas.
- `documentacao/`: manual, decisões e relatório.

## Convenções

Novas mensagens, comentários e documentação em português-BR. Identificadores novos em português, quando possível. Os módulos recebidos são preservados com seus nomes para compatibilidade com os modelos serializados. Dados e resultados entram na geração como evidências, nunca como instruções.

## Aceite

1. Consultar um motor em um período e retornar valores que coincidam com o banco e os scores exportados.
2. Relacionar dados operacionais e trechos documentais, identificando a origem de ambos.
3. Declarar ausência de informação ao consultar manutenção inexistente, sem inventar intervenções.
4. Pedir esclarecimento para motor ambíguo, rejeitar período inválido e tratar erros de API sem simular sucesso.
5. Demonstrar os três cenários com respostas reais da API e preservar evidências.
6. Entregar código, README, dependências, PDF e pacote sem credenciais.

## Limites

A API tem consumo pago; a avaliação usará poucas chamadas delimitadas. A aplicação é de demonstração local, sem autenticação para publicação. Os dados são sintéticos. Classificação, severidade e scores não substituem avaliação profissional. A validação do RAG será funcional em um corpus pequeno, sem alegação de precisão industrial.
