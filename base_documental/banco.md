# Banco de Dados: motor.db

Banco SQLite com dados sintéticos de sensores de motores industriais. Cada leitura registra rotação, vibração, temperatura e corrente em um instante, junto com um rótulo de falha. A base serve para treinar modelos de manutenção preditiva.

Arquivo: `motor.db` (SQLite 3)
Volume: 20 motores, 1.500 leituras por motor, 30.000 linhas no total.
Distribuição de classes: aproximadamente 87,6% normal e 12,4% falhas.

## Tabelas

### `motores`

Cadastro de equipamentos.

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `motor_id` | INTEGER PK | Identificador único do motor (1 a 20) |
| `fabricante` | TEXT | WEG, Siemens, ABB ou Toshiba |
| `modelo` | TEXT | Linha do produto (W22, 1LE0, M3BP, EQP-Global) |
| `potencia_kw` | REAL | Potência nominal em kW (7,5 a 22) |
| `ano_instalacao` | INTEGER | Ano de comissionamento (2018 a 2025) |

### `leituras`

Séries temporais dos sensores, com uma leitura por minuto.

| Coluna | Tipo | Unidade | Descrição |
| --- | --- | --- | --- |
| `motor_id` | INTEGER | n/a | FK para `motores.motor_id` |
| `timestamp` | TIMESTAMP | n/a | Data/hora da amostra |
| `rotacao_rpm` | REAL | RPM | Rotação do eixo, em regime normal perto de 1.700 a 1.850 RPM |
| `vibracao_mm_s` | REAL | mm/s | Velocidade RMS de vibração no mancal |
| `temperatura_c` | REAL | graus C | Temperatura da carcaça |
| `corrente_a` | REAL | A | Corrente de linha |
| `falha` | INTEGER | n/a | Código da falha |

### `tipos_falha`

| Código | Nome | Descrição |
| --- | --- | --- |
| 0 | Normal | Operação dentro dos parâmetros esperados |
| 1 | Desbalanceamento | Vibração alta e rotação instável |
| 2 | Superaquecimento | Temperatura e corrente elevadas |
| 3 | Falha mecânica | Queda de rotação com vibração e corrente altas |

## Como os dados foram simulados

Cada motor tem valores nominais ligeiramente diferentes, e cada leitura é gerada com ruído gaussiano em torno desses valores. Entre 3 e 6 janelas de falha são inseridas por motor, com rampa progressiva. Isso simula deterioração gradual e permite estudar antecipação de falhas.

Padrões característicos:

- Desbalanceamento (`1`): vibração sobe 4 a 8 mm/s; rotação ganha ruído extra.
- Superaquecimento (`2`): temperatura sobe 15 a 30 graus C; corrente sobe 2 a 4 A.
- Falha mecânica (`3`): rotação cai 200 a 400 RPM; vibração sobe 3 a 6 mm/s; corrente sobe 1,5 a 3 A.

O rótulo `falha` é atribuído apenas quando a rampa já está pronunciada, acima de cerca de 40% da intensidade. Amostras imediatamente anteriores ao rótulo podem mostrar o padrão emergindo, o que motiva features de janela móvel em sprints futuras.
