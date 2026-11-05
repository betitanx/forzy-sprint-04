# Conferência dos requisitos da Sprint 04

Revisão de 4 de novembro de 2026. Referência: enunciado da documentação final da solução fornecido pela equipe.

| Requisito | Evidência | Resultado |
| --- | --- | --- |
| 1. Visão geral | PDF, seção 1; README | Problema, público, escopo, benefícios esperados e funcionalidades descritos. |
| 2. Dados | PDF, seção 2; `motor.db`; `evidencias/qualidade_dados.json` | Fontes, período, variáveis, unidades, ativos, tratamentos e caráter sintético documentados. A ausência de manutenção e manuais de fabricante está explícita. |
| 3. Arquitetura | PDF, seção 3; `operacao.py`, `recuperacao.py`, `assistente.py`, `app.py` | Fluxo, responsabilidades e integração entre os modelos e o assistente explicados. |
| 4. Modelos | PDF, seção 4; módulos das sprints; arquivos de métricas | Classificador, baseline e Isolation Forest descritos, com treinamento, avaliação, resultados e justificativas. Reprodução registrada. |
| 5. RAG | PDF, seção 5; `recuperacao.py`; `base_documental/manifesto.json` | Preparação, indexação, busca, filtros, contexto, geração e fontes documentados. A busca é lexical, sem embeddings remotos. |
| 6. Assistente | PDF, seção 6; interface; testes locais e cenários | Uso, ambiguidades, ausência de informação e limites para intervenção física descritos. A consulta de manutenção informa a ausência dos registros. |
| 7. Testes e resultados | PDF, seção 7; `evidencias/cenarios.json`; capturas e registros | Três cenários completos com entrada, esperado, obtido e análise. A revisão adicionou proteção para citações agrupadas inválidas. |
| 8. Instalação e execução | PDF, seção 8; README; `requirements-lock.txt`; `preparar_projeto.py` | Ambiente, variáveis, preparação dos modelos, indexação e inicialização descritos. GitHub pode funcionar sem armazenar modelos grandes. |
| 9. Limitações e continuidade | PDF, seção 9; README | Limitações dos dados, modelos, busca e geração, além de prioridades futuras, registradas. |
| 10. Organização final | PDF, seção 10; repositório público `betitanx/forzy-sprint-04` | Entrega composta pelo PDF e pelo GitHub. Código, documentação, fontes e evidências organizados. Credenciais, ambientes virtuais e temporários excluídos. |

## Correções realizadas nesta revisão

- Padronização do PDF em Arial 12: texto preto, detalhes azuis e linguagem mais direta.
- Complementação da documentação sobre dados ausentes, duplicatas, frequência e preparação.
- Preparação reproduzível dos modelos para quem obtiver o projeto pelo GitHub.
- Correção da conferência de referências agrupadas, como `[O1, F99]`, com teste de regressão.
- Preparação local dos modelos para manter apenas os arquivos necessários no GitHub.
- Título da capa com a identificação Generative AI & Advanced Nets, maior separação entre os blocos dos modelos, horários de execução em formato brasileiro e instrução breve de acesso à aplicação.

## Limitações que não foram transformadas em funcionalidades

Não existem dados reais de operação, registros de manutenção ou manuais de fabricante no material recebido. A solução usa documentação da base e dos modelos e um guia acadêmico de interpretação. A documentação atende ao escopo demonstrado, mas não afirma validação industrial, diagnóstico definitivo ou integração a ordens de serviço.

Os testes conversacionais são exemplos executados, não uma garantia geral de precisão. As verificações automáticas das referências conferem identificadores e não substituem a análise do conteúdo.
