"""Relatório de entrega em Arial 12, com texto preto e detalhes azuis."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

RAIZ = Path(__file__).resolve().parents[1]
REPOSITORIO = "https://github.com/betitanx/forzy-sprint-04"
AZUL = colors.HexColor("#175EA8")
AZUL_CLARO = colors.HexColor("#EDF4FC")
PRETO = colors.black


def formatar_horario_brasil(valor):
    data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if data.tzinfo is None:
        raise ValueError("O registro de execução precisa informar seu fuso horário.")
    return data.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y às %H:%M:%S") + " (horário de Brasília)"


class Fluxo(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 480, 300

    def draw(self):
        c = self.canv
        caixas = [(163,260,154,34,["Interface local"]),(163,206,154,34,["Validação dos filtros"]),(0,130,146,50,["Dados e resultados"]),(167,130,146,50,["Modelos das", "Sprints 02 e 03"]),(334,130,146,50,["Documentos e", "busca TF-IDF"]),(160,63,160,43,["Contexto com fontes"]),(160,0,160,43,["OpenAI e validação"])]
        for x,y,w,h,linhas in caixas:
            c.setFillColor(colors.white)
            c.setStrokeColor(AZUL)
            c.roundRect(x,y,w,h,5,stroke=1,fill=1)
            c.setFillColor(PRETO)
            c.setFont("ArialEntrega",12)
            for i,linha in enumerate(linhas):
                c.drawCentredString(x+w/2,y+h/2+(len(linhas)-1)*7-i*14-4,linha)
        for x1,y1,x2,y2 in [(240,260,240,240),(240,206,73,180),(240,206,240,180),(240,206,407,180),(73,130,210,106),(240,130,240,106),(407,130,270,106),(240,63,240,43)]:
            c.setStrokeColor(AZUL)
            c.line(x1,y1,x2,y2)


def gerar():
    for nome,arquivo in [("ArialEntrega","arial.ttf"),("ArialEntregaNegrito","arialbd.ttf")]:
        pdfmetrics.registerFont(TTFont(nome,str(Path("C:/Windows/Fonts")/arquivo)))
    pdfmetrics.registerFontFamily("ArialEntrega",normal="ArialEntrega",bold="ArialEntregaNegrito")
    corpo = ParagraphStyle("Corpo",fontName="ArialEntrega",fontSize=12,leading=16,spaceAfter=8,textColor=PRETO)
    titulo = ParagraphStyle("Titulo",parent=corpo,fontName="ArialEntregaNegrito",spaceBefore=6,spaceAfter=10,keepWithNext=True)
    subtitulo = ParagraphStyle("Subtitulo",parent=titulo,spaceBefore=10,spaceAfter=7)
    celula = ParagraphStyle("Celula",parent=corpo,leading=15,spaceAfter=0)
    elementos, md = [], []
    cenarios=json.loads((RAIZ/"evidencias/cenarios.json").read_text(encoding="utf-8"))
    indice=json.loads((RAIZ/"evidencias/indice_documental.json").read_text(encoding="utf-8"))["inventario"]
    qualidade=json.loads((RAIZ/"evidencias/qualidade_dados.json").read_text(encoding="utf-8"))
    metricas=json.loads((RAIZ/"metricas_anomalias.json").read_text(encoding="utf-8"))["metricas_teste"]
    classificacao=json.loads((RAIZ/"metricas_modelo.json").read_text(encoding="utf-8"))
    verificacao=json.loads((RAIZ/"evidencias/verificacao_navegador.json").read_text(encoding="utf-8"))
    if not all(c["verificacao_automatica"] for c in cenarios) or verificacao["status_chat"]!=200:
        raise RuntimeError("As evidências não confirmam a conclusão dos cenários.")

    def par(texto,estilo=corpo):
        elementos.append(Paragraph(html.escape(texto).replace("\n","<br/>"),estilo))
        md.append(texto+"\n")

    def secao(texto):
        elementos.append(PageBreak())
        par(texto,titulo)
        elementos.append(HRFlowable(width="100%",thickness=1,color=AZUL,spaceAfter=10))
        md.append("\n## "+texto+"\n")

    def sub(texto):
        par(texto,subtitulo)

    def tab(cabecalho,linhas,larguras):
        dados=[[Paragraph(html.escape(str(c)),celula) for c in cabecalho]]
        dados += [[Paragraph(html.escape(str(c)).replace("\n","<br/>"),celula) for c in linha] for linha in linhas]
        t=Table(dados,colWidths=larguras,repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),AZUL_CLARO),("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,0),1,AZUL),("LINEBELOW",(0,1),(-1,-1),.25,AZUL),("LEFTPADDING",(0,0),(-1,-1),6),("RIGHTPADDING",(0,0),(-1,-1),6),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        elementos.extend([t,Spacer(1,10)])
        md.append("| "+" | ".join(cabecalho)+" |\n| "+" | ".join("---" for _ in cabecalho)+" |\n"+"\n".join("| "+" | ".join(str(c).replace("\n"," ") for c in linha)+" |" for linha in linhas)+"\n")

    def numero(valor):
        return f"{valor:.4f}".replace(".",",")

    elementos.append(Spacer(1,25*mm))
    par("FORZY",titulo)
    par("Documentação final da solução - Sprint 04 Generative AI & Advanced Nets",titulo)
    elementos.append(HRFlowable(width="100%",thickness=2,color=AZUL,spaceAfter=16))
    par("Assistente conversacional para análise de motores, com classificação de falhas, detecção de anomalias e recuperação de documentos.")
    par("Versão revisada para entrega - 4 de novembro de 2026.")
    par("Os dados são sintéticos. Os resultados apresentados foram verificados em ambiente local e não representam validação industrial.")
    sub("Equipe")
    tab(["Integrante","RM"],[["Lucca Phelipe Masini","564121"],["Luiz Henrique Poss","562177"],["Igor Paixão Sarak","563726"],["Bernardo Braga Perobeli","562468"],["Felipe Stefani Honorato","563380"]],[360,120])

    secao("1. Visão geral da solução")
    par("A solução reúne informações que normalmente precisam ser consultadas separadamente: leituras de sensores, resultados dos modelos e documentação. O objetivo é ajudar equipes de operação e manutenção a investigar comportamentos fora do padrão e entender os limites de cada conclusão.")
    par("O usuário pode consultar um motor em um período, verificar anomalias, analisar uma nova leitura e pedir explicações apoiadas nos documentos disponíveis. Reduzir tempo de investigação e priorizar inspeções são benefícios esperados; esta entrega não mede redução de custos nem prevenção de falhas reais.")
    tab(["Componente","Situação na entrega"],[["Classificação de falhas","Modelo e código reaproveitados da Sprint 02."],["Detecção de anomalias","Baseline por motor e Isolation Forest reaproveitados da Sprint 03."],["Assistente e RAG","Interface integrada e busca documental implementadas na Sprint 04."],["Manutenção realizada","Não há registros de serviços ou trocas de peças na base."],["Manuais dos fabricantes","Não foram fornecidos. O guia de interpretação é material da equipe."]],[170,310])
    par("O enunciado da Sprint 04 pede que o estado real do projeto seja documentado. Por isso, esta entrega separa funcionalidades implementadas, resultados verificados e melhorias futuras. Não se presume que a ausência de RAG nas sprints anteriores seja erro da equipe ou da avaliação: os enunciados anteriores não foram analisados.")

    secao("2. Dados utilizados e tratamentos")
    par("A fonte operacional é motor.db, um banco SQLite com 20 motores e 30.000 leituras, sendo 1.500 por motor. O período é de 01/01/2026 às 00h00 até 02/01/2026 às 00h59. As leituras têm intervalo de um minuto. Os horários não têm fuso informado e são utilizados na interface como aparecem na base.")
    tab(["Campo","Descrição e unidade"],[["motor_id","Identificador do equipamento; seleciona o cadastro e a referência normal."],["timestamp","Data e hora da leitura; define ordem e recorte temporal."],["rotacao_rpm","Rotação do eixo, em RPM."],["vibracao_mm_s","Vibração, em milímetros por segundo."],["temperatura_c","Temperatura, em graus Celsius."],["corrente_a","Corrente elétrica, em ampères."],["falha","Rótulo histórico: 0 normal; 1 desbalanceamento; 2 superaquecimento; 3 falha mecânica."]],[155,325])
    par("A tabela motores registra fabricante, modelo, potência e ano de instalação. A tabela tipos_falha descreve as quatro classes. Existem 26.291 leituras normais, 1.205 de desbalanceamento, 1.718 de superaquecimento e 786 de falha mecânica.")
    sub("Qualidade e preparação")
    par(f"A conferência encontrou {sum(qualidade['nulos_sensores'].values())} valores ausentes nos quatro sensores e {qualidade['pares_motor_instante_duplicados']} pares de motor e instante duplicados. Não houve valores negativos de rotação, vibração ou corrente. Os 29.980 intervalos entre leituras consecutivas medem 60 segundos.")
    par("Os registros são ordenados por motor e instante. O classificador padroniza as quatro variáveis antes do treinamento. O detector aprende a referência normal apenas com leituras normais da partição de treino. Não foi necessário preencher dados ausentes ou remover duplicatas na base entregue. Uma nova leitura com valor não finito é rejeitada.")
    par("A simulação inclui ruído e rampas de deterioração. O rótulo de falha aparece após 40% da intensidade da rampa; por isso, um desvio pode surgir antes do rótulo. Não existem ordens de serviço, técnicos ou histórico de troca de peças. Os documentos do RAG descrevem a base e os modelos, e não comprovam procedimentos de um fabricante.")

    secao("3. Arquitetura da solução")
    elementos.extend([Fluxo(),Spacer(1,18)])
    par("A interface envia a pergunta, o motor e o período ao servidor local. operacao.py valida os filtros, consulta o banco em modo de leitura e reúne os resultados. Quando necessário, também executa o classificador e o detector para uma leitura.")
    par("recuperacao.py busca trechos nos documentos. assistente.py junta esses trechos aos resultados operacionais e pede uma resposta à OpenAI. Antes da apresentação, os identificadores das fontes são conferidos. A resposta retorna à interface com as evidências consultadas.")
    par("O projeto usa Python, SQLite, pandas, NumPy, scikit-learn, joblib, pypdf e o SDK da OpenAI. A interface utiliza HTML, CSS e JavaScript, sem compilação. A chave fica no servidor; não é enviada ao navegador. Nenhuma resposta aciona fisicamente os equipamentos.")
    par("A validação repetiu os três treinamentos e reproduziu as matrizes de confusão originais. As métricas completas acompanham o código. No processamento posterior, janelas de cinco leituras resumem a persistência dos scores; elas não são entradas dos detectores.")

    secao("4. Modelos de inteligência artificial")
    sub("Classificação de falhas - Sprint 02")
    par("O classificador padroniza os quatro sensores com StandardScaler e usa ExtraTrees: 500 árvores, mínimo de três amostras por folha e semente 43. Os pesos balanceados compensam a menor presença das classes de falha.")
    par("A divisão cronológica por motor reserva 21.000 leituras para treino (70%) e 9.000 para teste (30%). Foi mantida a versão anterior de maior recall das falhas. O teste não representa validação externa independente dessa seleção.")
    tab(["Classe","Precisão","Recall","F1"],[[nome,numero(classificacao['classification_report'][nome]['precision']),numero(classificacao['classification_report'][nome]['recall']),numero(classificacao['classification_report'][nome]['f1-score'])] for nome in ["Normal","Desbalanceamento","Superaquecimento","Falha mecânica"]],[195,95,95,95])
    par("A acurácia foi 0,9638 e o F1 macro foi 0,8868. Precisão indica a proporção de acertos entre os casos classificados em uma classe; recall indica quanto dos casos reais dessa classe foi encontrado. F1 equilibra as duas medidas.")
    elementos.append(Spacer(1,12))
    sub("Referência normal e anomalias - Sprint 03")
    par("A divisão cronológica por motor usa 16.800 registros no treino (56%), 4.200 na validação (14%) e 9.000 no teste (30%). O ajuste usa somente exemplos normais. Os rótulos selecionam esse treino e servem à calibração e à avaliação; não são atributos de entrada.")
    par("O baseline resume os desvios dos quatro sensores em relação à média e ao desvio-padrão normal do motor. O Isolation Forest usa 400 árvores, semente 42 e oito entradas normalizadas: quatro desvios assinados e seus valores absolutos.")
    tab(["Método","Precisão","Recall","F1"],[["Baseline por motor",numero(metricas['baseline_estatistico']['precision_anomalia']),numero(metricas['baseline_estatistico']['recall_anomalia']),numero(metricas['baseline_estatistico']['f1_anomalia'])],["Isolation Forest",numero(metricas['isolation_forest']['precision_anomalia']),numero(metricas['isolation_forest']['recall_anomalia']),numero(metricas['isolation_forest']['f1_anomalia'])]],[195,95,95,95])
    par("A validação escolheu os limiares de maior F1: 2,4666 no baseline e 0,0854 no Isolation Forest. O baseline é a saída principal por precisão e F1; o Isolation Forest tem maior recall e mais falsos positivos. A PR-AUC foi 0,9853 e 0,9370, respectivamente.")

    secao("5. Recuperação de documentos - RAG")
    par("RAG é a geração apoiada em informações recuperadas. A busca seleciona trechos, e a OpenAI redige a resposta usando esses trechos e os resultados calculados localmente.")
    par(f"Há {indice['documentos']} documentos e {indice['fragmentos']} fragmentos: o PDF do banco, BANCO.md, DADOS_FORZY.md, COMPARACAO_SPRINTS.md e o guia da equipe. Todas as origens são identificadas; o guia não é um manual de fabricante.")
    tab(["Etapa","Como funciona"],[["Preparação","PDFs têm o texto extraído com a página de origem. Textos e Markdown são lidos em UTF-8."],["Fragmentação","Trechos de até 180 palavras, com 30 palavras de sobreposição para preservar contexto."],["Indexação","TF-IDF atribui pesos a palavras e pares de palavras. O índice é local e fica em memória."],["Busca","Similaridade de cosseno seleciona até cinco trechos com pontuação mínima de 0,035."],["Metadados","Arquivo, título, página, identificador e hash ligam o trecho à versão da fonte."],["Geração","gpt-4.1-mini é o padrão configurável. A resposta usa o contexto fornecido e uma estrutura JSON validada."]],[120,360])
    par("O filtro operacional aplica motor e período às leituras. O manifesto documental pode restringir uma fonte a motores e datas de vigência. Documentos sem restrições são gerais. Essa vigência é diferente da data da leitura. A filtragem documental foi testada com arquivos de teste; o corpus inicial é geral.")
    par("As instruções de geração exigem português-BR, uso das evidências, distinção entre previsão e diagnóstico e reconhecimento de informação ausente. Também proíbem inventar manuais, serviços ou limites técnicos. A instrução completa está em assistente.py.")
    par("O1 identifica a fonte operacional, C1 identifica uma leitura fornecida pelo usuário e F1 em diante identifica os documentos daquela resposta. A interface permite abrir cada fonte. Identificadores inexistentes são rejeitados, inclusive em citações agrupadas como [O1, F2]. Essa verificação não garante, sozinha, que toda conclusão seja correta.")
    par("A opção por busca local reduz dependências e facilita conferir as fontes deste corpus pequeno. Não há embeddings remotos nem banco vetorial externo. A busca lexical pode falhar em paráfrases, e sua pontuação não é uma probabilidade de acerto. PDFs sem camada de texto exigem OCR antes da inclusão.")

    secao("6. Uso do assistente")
    par("1. Selecione um motor ou a opção de todos os motores. 2. Informe início e fim nos filtros. 3. Escreva a pergunta ou escolha um exemplo. 4. Leia a resposta e abra as fontes em Evidências. 5. Se desejar, exporte a conversa em JSON.")
    par("Para uma nova leitura, abra Nova leitura e informe rotação, vibração, temperatura e corrente. A aplicação executa os dois tipos de modelo e apresenta os resultados junto do contexto. Nova conversa apaga o histórico mantido pelo navegador.")
    par("Os filtros definem o período consultado. Expressões como ontem não são convertidas automaticamente em datas. Se a pergunta mencionar um motor diferente do filtro, a aplicação pede correção. Se não houver dados no recorte, ela não substitui o período por outro silenciosamente.")
    par("Exemplos atendidos: investigar anomalias do motor 3; comparar seus sensores com a referência normal; explicar os sinais descritos na documentação; e consultar um serviço de manutenção. Neste último caso, a resposta informa que o histórico não existe na base, em vez de inventar uma intervenção.")
    par("A aplicação mantém até seis mensagens como contexto da conversa. A severidade mostrada é uma regra do projeto baseada no score. Ela não equivale a uma classificação validada de risco industrial. Procedimentos físicos dependem de documentação adequada e avaliação de um profissional responsável.")

    secao("7. Testes e resultados")
    par("A revisão cobre testes locais, reprodução dos modelos, conferência dos dados, execução dos três cenários exigidos e inspeção da interface. As respostas abaixo foram efetivamente obtidas da OpenAI e estão preservadas em evidencias/cenarios.json. Novas execuções podem produzir redações diferentes.")
    for i,cenario in enumerate(cenarios):
        if i:
            elementos.append(PageBreak())
        sub(f"Cenário {i+1}: "+["falha ou anomalia","dados e documentação","informação insuficiente"][i])
        par("Entrada: "+cenario['pergunta'])
        par("Recorte: motor 3, de 01/01/2026 às 17h30 até 02/01/2026 às 00h59.")
        par("Resultado esperado: "+cenario['esperado'])
        sub("Resultado obtido")
        par(cenario['resultado']['resposta'])
        tab(["Fonte","Origem consultada"],[[f['id'],f['arquivo']+(f" - página {f['pagina']}" if f.get('pagina') else '')] for f in cenario['resultado']['fontes']],[65,415])
        sub("Análise")
        par(["Os números correspondem ao recorte: 450 leituras, 2 alertas do baseline, 4 do Isolation Forest e 4 leituras anômalas únicas. O maior score foi aproximadamente 6,1552. A última leitura, isoladamente, foi normal segundo o classificador e ficou abaixo do limiar do detector. Portanto, a condição final não apaga os alertas anteriores.","A resposta reúne a fonte operacional e documentos recuperados. A explicação é limitada à base sintética e ao guia da equipe, sem alegar que houve consulta a manual de fabricante. O roteiro orienta a investigação, sem prescrever intervenção física.","A resposta reconhece a ausência do histórico e não inventa data, técnico ou troca de peça. O teste demonstra esse comportamento no exemplo executado, sem garantir ausência de alucinações em qualquer pergunta."][i])
        par("Registro de execução: "+formatar_horario_brasil(cenario['executado_em_utc'])+".\nModelo retornado: "+cenario['resultado']['modelo']+". Duração: "+str(cenario['resultado']['duracao_segundos']).replace(".",",")+" segundos.")
    sub("Outras verificações")
    par("A revisão atual ampliou a suíte para 12 testes locais. Eles cobrem períodos inválidos, motor inexistente, falta de leituras, valores não finitos, divergência de motor, restrições documentais, busca sem correspondência, citações inexistentes e contagem sem duplicidade entre detectores.")
    par("A interface foi verificada em Chromium nas larguras de 320, 768, 1.024 e 1.440 pixels, sem rolagem horizontal. A consulta recebeu HTTP 200 e exibiu as fontes, sem erros de console. As capturas estão em evidencias/. Foram mantidas fora do corpo deste PDF para preservar a padronização tipográfica e de cores solicitada.")

    secao("8. Instalação, preparação e execução")
    par("Requisitos: Python 3.13, acesso à internet para instalar dependências e consultar a OpenAI, e uma chave válida para o projeto escolhido. O uso da API depende do acesso ao modelo e da disponibilidade de saldo ou limite. Os testes locais e a preparação dos modelos não exigem chamada à API.")
    sub("Obter o projeto")
    par("Clone o repositório público indicado na seção 10. Ele contém o código e a base necessários para preparar os modelos no computador de quem executará o projeto, sem depender de arquivos existentes no computador da equipe.")
    sub("Instalar as dependências")
    for comando in ["python -m venv .venv",r".\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt"]:
        par(comando)
    sub("Configurar a chave")
    par("Copie .env.example para .env.local e preencha OPENAI_API_KEY de forma privada. OPENAI_MODEL é opcional e tem gpt-4.1-mini como padrão. A chave não deve entrar no GitHub, em capturas ou em registros de execução.")
    sub("Preparar e iniciar")
    for comando in [r".\.venv\Scripts\python.exe preparar_projeto.py",r".\.venv\Scripts\python.exe indexar_documentos.py",r".\.venv\Scripts\python.exe app.py"]:
        par(comando)
    par("Após iniciar o servidor, abra http://localhost:8501 no navegador da mesma máquina. Localhost, também representado por 127.0.0.1, sempre aponta para o próprio computador de quem usa o endereço. Cada avaliador deve executar o projeto no seu PC; esse endereço não acessa o computador da equipe.")
    par("Os comandos acima preparam os modelos ausentes, indexam os documentos e iniciam o servidor local, nessa ordem. Para encerrar, pressione Ctrl+C no terminal.")
    par("Para testar, execute python -m unittest discover -s testes -v pelo Python do ambiente virtual. avaliar_cenarios.py faz três chamadas reais à API, pode ter custo e atualiza suas evidências. Não é necessário executá-lo para simplesmente abrir o projeto.")
    par("Se a chave não for aceita, confira a configuração privada. Se houver erro de saldo ou limite, confira o projeto OpenAI. Se faltarem os modelos ou o CSV de resultados, execute preparar_projeto.py. Para mudar a porta, use app.py --porta 8502. As versões completas do ambiente testado estão em requirements-lock.txt.")

    secao("9. Limitações e continuidade")
    par("A solução é acadêmica e usa dados simulados de um período curto. Ainda não há validação em equipamentos reais, ingestão contínua, ordens de serviço, autenticação de vários usuários ou integração para executar ações físicas. Não se deve tratar uma previsão como diagnóstico confirmado.")
    par("Os documentos disponíveis explicam os dados e os modelos. A resposta sobre procedimentos é restrita a esse material. O projeto não possui manuais de fabricante nem histórico de manutenção; a ausência está documentada e faz parte do terceiro cenário de teste.")
    par("A busca pode omitir trechos relevantes quando a pergunta usa palavras diferentes. A geração pode interpretar incorretamente uma fonte mesmo quando seu identificador existe. O gráfico da interface resume a série para exibição; os totais usam todas as leituras filtradas.")
    tab(["Prioridade","Próxima evolução"],[["Alta","Adicionar manuais e registros de manutenção autorizados, com identificação do ativo e versão."],["Alta","Avaliar dados reais e respostas com especialistas, antes de uso industrial."],["Alta","Ampliar testes de sustentação das respostas, informação ausente e ataques ao contexto."],["Média","Comparar a busca lexical com busca semântica e medir a recuperação em corpus maior."],["Média","Rever limiares e severidade conforme os custos reais de erros e alertas."],["Média","Adicionar autenticação e ingestão contínua somente se o projeto evoluir além do uso local."]],[85,395])

    secao("10. Organização e conferência da entrega")
    par("A entrega é composta por este PDF e pelo repositório público no GitHub, que reúne o material necessário à execução e à análise técnica. O README apresenta a visão geral, a estrutura e os comandos. Os modelos são preparados localmente pelo código disponível no repositório.")
    elementos.append(Paragraph('<link href="'+REPOSITORIO+'" color="#175EA8">'+REPOSITORIO+'</link>',corpo))
    md.append(REPOSITORIO+"\n")
    tab(["Requisito","Local de conferência"],[["1. Visão geral","Seção 1."],["2. Dados","Seção 2 e evidencias/qualidade_dados.json."],["3. Arquitetura","Seção 3 e módulos do projeto."],["4. Modelos","Seção 4, métricas e reprodução registrada."],["5. RAG","Seção 5, recuperacao.py e assistente.py."],["6. Assistente","Seção 6 e interface web."],["7. Testes","Seção 7 e pasta evidencias/."],["8. Execução","Seção 8, README e preparar_projeto.py."],["9. Limitações","Seção 9."],["10. Organização","Este PDF e o repositório público."]],[180,300])
    par("A revisão conclui que os dez itens estão documentados para o escopo implementado. As limitações não foram transformadas em funcionalidades fictícias. A avaliação acadêmica e a aceitação final continuam a cargo do professor.")
    par("Referências externas: documentação oficial OpenAI sobre saídas estruturadas em developers.openai.com/api/docs/guides/structured-outputs e chamada de funções em developers.openai.com/api/docs/guides/function-calling. As fontes operacionais e de domínio são os arquivos fornecidos nas sprints, identificados no projeto.")

    def rodape(c,doc):
        c.saveState()
        c.setStrokeColor(AZUL)
        c.line(20*mm,18*mm,190*mm,18*mm)
        c.setFillColor(PRETO)
        c.setFont("ArialEntrega",12)
        c.drawString(20*mm,11*mm,"Forzy - Sprint 04")
        c.drawRightString(190*mm,11*mm,str(doc.page))
        c.restoreState()

    destino=RAIZ.parent/"Documentacao_final_Sprint_04.pdf"
    SimpleDocTemplate(str(destino),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=20*mm,bottomMargin=25*mm,title="Forzy - Documentação final revisada da Sprint 04",author="Equipe Forzy").build(elementos,onFirstPage=rodape,onLaterPages=rodape)
    (RAIZ/"documentacao/RELATORIO_FINAL.md").write_text("# Forzy - Documentação final revisada\n\n"+"\n".join(md),encoding="utf-8")
    print(json.dumps({"pdf":str(destino),"bytes":destino.stat().st_size},ensure_ascii=False))
