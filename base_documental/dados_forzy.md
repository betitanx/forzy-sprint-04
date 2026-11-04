# Dados Históricos da Forzy

## Origem e escopo

Nesta entrega, o arquivo histórico disponibilizado para a equipe é `motor.db`, um banco SQLite com leituras sintéticas de motores industriais. Ele é tratado como a fonte histórica usada na Sprint 3. A documentação de origem fornecida com o banco está preservada em `documentação.pdf`.

## Volume e período

- 20 motores cadastrados.
- 30.000 leituras no total.
- 1.500 leituras por motor.
- Frequência: uma leitura por minuto.
- Período: de `2026-01-01 00:00:00` a `2026-01-02 00:59:00`.
- Tabelas: `motores`, `leituras` e `tipos_falha`.

## Variáveis utilizadas

| Variável | Tipo | Papel | Unidade | Uso na Sprint 3 |
| --- | --- | --- | --- | --- |
| `motor_id` | inteiro | Identificador do equipamento | n/a | Seleciona o perfil normal específico do motor |
| `timestamp` | data/hora | Ordem temporal | n/a | Divide treino, validação e teste |
| `rotacao_rpm` | real | Sensor | RPM | Entrada do perfil e dos modelos |
| `vibracao_mm_s` | real | Sensor | mm/s | Entrada do perfil e dos modelos |
| `temperatura_c` | real | Sensor | graus C | Entrada do perfil e dos modelos |
| `corrente_a` | real | Sensor | A | Entrada do perfil e dos modelos |
| `falha` | inteiro | Evento/rótulo histórico | n/a | Não entra no treinamento; serve para avaliação |

A tabela `motores` contém metadados como fabricante, modelo, potência e ano de instalação. Esses metadados não entram no detector final porque o objetivo é reconhecer desvios no comportamento dos sensores e permitir inferência mesmo quando somente a leitura está disponível.

## Rótulos conhecidos

| Código | Classe |
| --- | --- |
| 0 | Normal |
| 1 | Desbalanceamento |
| 2 | Superaquecimento |
| 3 | Falha mecânica |

Os rótulos são usados para criar a referência de avaliação `anomalia conhecida = falha > 0`. O detector não recebe esses rótulos durante o treinamento, preservando a característica semissupervisionada da abordagem.
