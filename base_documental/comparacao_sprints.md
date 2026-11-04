# Comparação entre as Sprints 2 e 3

## Sprint 2: classificação de falhas conhecidas

A Sprint 2 resolve uma classificação multiclasse supervisionada. Dadas as quatro leituras de sensores, o classificador estima uma das classes conhecidas: Normal, Desbalanceamento, Superaquecimento ou Falha mecânica. Ele é adequado quando os padrões de falha já estão representados e rotulados no histórico.

## Sprint 3: detecção de desvios

A Sprint 3 aprende o comportamento normal de cada motor e calcula o quanto uma nova leitura se afasta desse padrão. O detector pode apontar um desvio mesmo quando o tipo exato de falha não está entre as classes conhecidas. Por isso, ele é útil para triagem, investigação e identificação de desgaste ainda não rotulado.

## Como as abordagens se complementam

1. O detector de anomalias pode gerar um alerta de comportamento fora do padrão.
2. O classificador da Sprint 2 pode, em seguida, estimar o tipo de falha conhecida quando houver sinal compatível.
3. O agente pode comunicar os dois resultados separadamente: score e severidade do desvio, além da classe de falha mais provável.
4. Quando os resultados discordarem, o caso deve ser tratado como investigação, não como diagnóstico definitivo.

O detector não substitui o classificador: ele amplia a cobertura para desvios desconhecidos e ajuda a priorizar inspeções.

## Resultados da Sprint 3

No teste cronológico, o baseline estatístico obteve F1 de anomalia `0,9352`, recall `0,9553` e PR-AUC `0,9853`. O Isolation Forest obteve F1 `0,8898`, recall `0,9751` e PR-AUC `0,9370`. A diferença representa um trade-off operacional: o baseline produz menos falsos positivos, enquanto o Isolation Forest sinaliza mais anomalias e deve ser usado quando o custo de perder um desvio for maior.
