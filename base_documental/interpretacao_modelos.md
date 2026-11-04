# Guia de interpretação dos modelos

Origem: código e documentação das Sprints 02 e 03, consolidados pela equipe na Sprint 04. Este guia explica a implementação acadêmica; não é um manual de fabricante.

## Classificação de falhas

O classificador ExtraTrees recebe rotação em RPM, vibração em mm/s, temperatura em °C e corrente em ampères. As classes são normal, desbalanceamento, superaquecimento e falha mecânica. A probabilidade expressa a saída do modelo, não a certeza de um diagnóstico físico. A base é sintética.

## Score e baseline operacional

O baseline da Sprint 03 compara os quatro sensores com médias e desvios-padrão do período normal de treino do próprio motor. O score é a raiz da média dos quadrados dos desvios padronizados. O limiar estatístico calibrado é aproximadamente 2,4666. A classificação anômala ocorre quando o score alcança esse limiar. Há também um Isolation Forest multivariado complementar. O limiar do Isolation Forest é aproximadamente 0,0854.

## Interpretação de severidade

O código da Sprint 03 usa a razão entre score e limiar: abaixo de 0,75 é baixo; a partir de 0,75 é atenção; a partir de 1,0 é alto; a partir de 1,5 é crítico. Essa regra é uma heurística do projeto, sem validação como escala de risco industrial. Um score alto significa desvio estatístico, não comprova a causa de uma falha.

## Investigação dos desvios

Para investigar, conferir o motor, o período, as unidades e a qualidade do registro; comparar os sensores com a referência normal do equipamento; verificar se o desvio persiste em várias leituras; comparar a hipótese do classificador com a documentação disponível. Esse roteiro é uma orientação analítica da equipe. Intervenções físicas dependem do procedimento do fabricante e da avaliação de um profissional responsável. Não executar manobras elétricas, desmontagens ou alterações de proteção com base apenas no assistente.

## Falta de informações

O banco não contém ordens de serviço, nomes de técnicos, datas de troca de peças ou intervenções de manutenção. Não inferir que uma falha rotulada corresponde a uma manutenção realizada. Se a pergunta pedir esses dados, informar a ausência e solicitar o histórico de manutenção. Para motor não cadastrado, não afirmar que existe perfil específico; a função de inferência original pode utilizar referência global, mas consultas históricas devem indicar o cadastro ausente.

## Limitação da simulação

Os padrões da base foram construídos artificialmente. Nas rampas de falha, o desvio pode aparecer antes do rótulo histórico. Um alerta diante de rótulo normal não comprova sozinho erro do detector. As métricas obtidas nesta base não demonstram redução de custo, prevenção de incidentes ou desempenho em operação real.
