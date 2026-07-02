# pitchflow

> **Real-time football match-event streaming into a Delta lakehouse.**
> Kafka · Spark Structured Streaming · Delta Lake · Streamlit · StatsBomb

![CI](https://github.com/guisefe/pitchflow/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License: MIT](https://img.shields.io/github/license/guisefe/pitchflow)
![Last commit](https://img.shields.io/github/last-commit/guisefe/pitchflow)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/guisefe/pitchflow)

---

## What this is

`pitchflow` is a real-time data platform that turns a football match into a live analytics feed. A replay producer streams real StatsBomb event data into Kafka in match-clock order. Spark Structured Streaming consumes the topic and writes a Bronze → Silver → Gold Delta Lake medallion. A Streamlit dashboard reads the Gold tables live and renders score, xG race, win probability, momentum and a shot map as the match unfolds.

It runs locally with Docker Compose or one-click in GitHub Codespaces. No cloud bill, no paid data.

---

## Por que esse projeto

A maioria dos portfólios de engenharia de dados é batch — jobs agendados sobre tabelas finitas. Streaming é o que separa o nível pleno do sênior, e a curva é mais íngreme justamente porque o dado nunca para: é preciso raciocinar sobre *quando* é "agora", lidar com eventos atrasados e manter agregações com estado sem reler tudo.

Esse projeto foi construído pra demonstrar essas habilidades de ponta a ponta — com a mesma stack que uso no Databricks (Spark + Delta + Medallion), aplicada à sua forma mais difícil: stream contínuo em vez de batch.

**Decisão de domínio.** Dados de futebol em tempo real costumam ser pagos. O [StatsBomb Open Data](https://github.com/statsbomb/open-data) publica eventos profissionais gratuitamente — cada passe, condução e chute, com xG e coordenadas. É o dataset que a comunidade de football analytics usa de verdade. Usar ele transmite familiaridade com o ecossistema, não só com a tecnologia.

**Decisão de arquitetura.** Como dados *live* são pagos, faço o replay de uma partida real em ordem de relógio de jogo a velocidade configurável (60×, por padrão — uma partida de 90 minutos streama em ~90 segundos). Replay não é workaround: é um pattern legítimo de produção (é como se faz backfill e reprocessamento em sistemas de streaming), e torna o pipeline determinístico e reproduzível.

---

## Arquitetura

```
StatsBomb Open Data (eventos reais, gratuito)
        │  download + cache  (producer/download.py)
        ▼
┌─────────────────┐   replay em match-clock   ┌──────────────┐
│ Replay Producer │ ────────────────────────▶ │   Redpanda   │  topic: match.events
│ (producer/)     │                           │   (Kafka)    │
└─────────────────┘                           └──────┬───────┘
                                                     │
                             ┌───────────────────────▼──────────────────────┐
                             │         Spark Structured Streaming            │
                             │                                               │
                             │  Bronze   JSON cru (append, exactly-once)     │
                             │     │     streaming/bronze.py                 │
                             │     ▼                                         │
                             │  Silver   colunas tipadas + dedup + watermark │
                             │     │     streaming/silver.py                 │
                             │     ▼                                         │
                             │  Gold     métricas ao vivo (MERGE upsert)     │
                             │           streaming/gold.py                   │
                             │     • xg_timeline   corrida de xG por minuto  │
                             │     • match_state   placar + win probability  │
                             │     • shots         mapa de chutes            │
                             │     • momentum      dominância nos últimos 5' │
                             └───────────────────────┬──────────────────────┘
                                                     │  Delta Lake (ACID)
                             ┌───────────────────────▼──────────────────────┐
                             │  Streamlit live dashboard (dashboard/app.py)  │
                             │  auto-refresh a cada 3s · lê via deltalake    │
                             └──────────────────────────────────────────────┘
```

---

## Stack & decisões

| Camada | Ferramenta | Por quê escolhi |
|--------|-----------|-----------------|
| Event log | **Redpanda** (API Kafka) | Binário único, sem ZooKeeper, RAM baixa. Semântica Kafka completa sem o peso operacional — ideal pra rodar em Codespace ou laptop. |
| Stream processing | **Spark Structured Streaming** 3.5 | Padrão de mercado, espelha o Databricks que uso profissionalmente. Watermark e stateful aggregation são primitivas nativas — não precisa orquestrar à mão. |
| Formato de tabela | **Delta Lake** 3.2 | ACID em arquivos de objeto, sink idempotente via `txnAppId`/`txnVersion`, time travel. É a peça que torna "lakehouse" um conceito real e não buzzword. |
| Leitura no dashboard | **deltalake** (Python) | Lê Delta sem inicializar Spark — leve o suficiente pra refresh a cada 3s sem ficar caro. |
| Dashboard | **Streamlit** + **Plotly** | Rápido de construir, demoável ao vivo, sem precisar empacotar frontend separado. Custo: visual default. Aceitável dado o escopo. |
| Dados | **StatsBomb Open Data** | Gratuito, real, com xG e coordenadas. Único dataset público com essa granularidade. |

A spec completa de requisitos, riscos e trade-offs está em [`docs/PROJECT.md`](docs/PROJECT.md).

---

## Infrastructure

```yaml
# docker-compose.yml
services:
  redpanda:
    image: redpandadata/redpanda:v24.1.7
    command:
      - redpanda start
      - --smp 1 --memory 1G --overprovisioned
      - --kafka-addr internal://0.0.0.0:9092,external://0.0.0.0:19092
      - --advertise-kafka-addr internal://redpanda:9092,external://localhost:19092
    ports: ["19092:19092", "9644:9644"]
    healthcheck:
      test: ["CMD-SHELL", "rpk cluster health | grep -q 'Healthy:.*true'"]
      interval: 10s

  console:
    image: redpandadata/console:v2.6.0
    depends_on: [redpanda]
    ports: ["8080:8080"]
    environment:
      KAFKA_BROKERS: redpanda:9092
```

**Notas de design:**

- **Redpanda over Kafka.** Single binary, no ZooKeeper, no KRaft setup. Same wire protocol, fraction of the memory — fits in a Codespace.
- **Explicit memory cap.** `--memory 1G` declared upfront — não fica brigando com defaults imprevisíveis.
- **Real healthcheck, not `sleep`.** `make up` espera `Healthy: true` antes de criar o tópico.
- **Split listeners.** Internal (`redpanda:9092`) pra clientes dentro da rede Docker, external (`localhost:19092`) pro host. Evita a pegadinha mais comum de Kafka em Docker.

O ambiente de desenvolvimento está declarado em `.devcontainer/devcontainer.json` (Python 3.11, JDK 17, port forwarding). Abrir o repo em Codespaces é o único setup necessário.

---

## Quickstart

### GitHub Codespaces (recomendado)

Clica em **Open in Codespaces** no topo. O `.devcontainer` instala Python, Docker e dependências sozinho.

### Local

```bash
git clone https://github.com/guisefe/pitchflow.git
cd pitchflow

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

sudo apt-get install -y openjdk-17-jdk-headless   # Spark precisa de Java 17
cp .env.example .env
```

### Rodando o pipeline (5 terminais)

```bash
# Terminal 1 — Redpanda + cria o tópico
make up

# Terminal 2-4 — pipeline streaming (cada um fica rodando)
make bronze
make silver
make gold

# Terminal 5 — alimenta + visualiza
make replay
make dashboard      # http://localhost:8501
```

`make help` lista todos os comandos. `make reset` limpa estado para começar do zero.

---

## A história por trás de um bug

Na primeira vez que o pipeline rodou ponta a ponta, o placar saiu **Argentina 7 × 5 França**. Não foi a final que eu lembro de assistir.

Olhei a tabela `shots` da camada Gold. Sete chutes com xG idêntico de `0.7835`. Em uma partida real, isso é impossível — xG é um valor único por contexto. Mas reconheci o número: é o xG fixo de um pênalti no modelo do StatsBomb.

E aí caiu a ficha: o jogo foi pra disputa de pênaltis. O StatsBomb marca esses eventos com `period = 5`. Eu estava contando os pênaltis do shootout como gols do jogo.

A correção foi uma linha na camada Silver:

```python
.filter(F.col("period") <= 4)
```

Mas o aprendizado é maior que a linha. Por que não filtrei pelo *tipo* do chute (`Penalty`)? Porque o Messi marcou um pênalti aos 22 minutos — esse é gol legítimo. **Conhecer o domínio importa mais que conhecer o framework.** A diferença entre "pênalti de jogo" e "pênalti de shootout" não está em nenhuma documentação do Spark — está em saber futebol.

Depois da correção, o placar foi 3-3 e o xG da Argentina caiu de 5.89 para 2.76 — próximo do valor reportado pela literatura analítica para aquela final. A win probability ficou em 50%, o que à primeira vista parecia bug. Não era: empate técnico, sem tempo restante. O modelo está sendo brutalmente honesto — *não posso prever um shootout. Isso seria outro modelo, com features diferentes.*

Esse é o tipo de raciocínio que defendo numa entrevista.

---

## Conceitos de streaming, mapeados pro código

| Conceito | Onde está | Por quê importa |
|----------|-----------|-----------------|
| **Event replay** | `producer/replay.py` | Substitui dados live pagos; também é pattern real de backfill em produção |
| **Checkpoint** | `streaming/bronze.py` | Job restart retoma exatamente onde parou — sem perda nem duplicação |
| **Watermark** | `streaming/silver.py` | Limita o estado de dedup em memória; sem ele, o state cresce indefinidamente |
| **Dedup stateful** | `streaming/silver.py` | `dropDuplicates(["event_id"])` com watermark — exactly-once no Silver |
| **Idempotência Delta** | `streaming/silver.py` | `txnAppId + txnVersion` — replay do mesmo `batch_id` é no-op |
| **foreachBatch + MERGE** | `streaming/gold.py` | Único caminho oficial pra upsert em streaming com Delta |
| **Running state** | `streaming/gold.py` | xG acumula por time/minuto sem reler tudo — coração do streaming |
| **Sliding window** | `streaming/gold.py` | Momentum olha só os últimos 5 min, diferente do xG que é cumulativo |

---

## Qualidade

- **28 testes unitários em < 1 segundo**, sem broker e sem Spark. A lógica de negócio (relógio do jogo, classificação de eventos, xG, win probability) está isolada da infraestrutura em `streaming/metrics.py`, então é testável sozinha.
- **Lint (ruff) + tests rodam em todo push** via GitHub Actions. CI fica vermelha se algo regredir.
- O Bronze é **schema-on-read** (JSON cru). Isso permite reprocessar Silver/Gold com regras novas sem precisar re-ingerir do Kafka — foi essa decisão arquitetural que permitiu corrigir o bug do shootout sem perder dado.

---

## Considerações de Produção

Esse projeto roda em modo replay, com 1 partida, num ambiente controlado (Codespace/Docker local). Rodar em produção de verdade, com dado ao vivo e múltiplas partidas simultâneas, exigiria decisões adicionais:

**Escala.** Hoje o Spark processa 1 stream, 1 partida. Pra múltiplas partidas simultâneas, cada uma teria seu próprio tópico Kafka (`match.events.{match_id}`) e os dados no Delta seriam particionados por `match_id`. O gargalo real não seria o Kafka — ele escala horizontalmente sem esforço — seria o cluster Spark, que precisaria de auto-scaling (em Databricks, isso é nativo via Jobs Compute).

**Confiabilidade.** O pipeline já foi projetado pra sobreviver a falhas: o Delta Lake garante transações ACID, então se o Spark cair no meio de um `MERGE`, a transação simplesmente não é commitada. Ao reiniciar, o job lê o checkpoint (`data/checkpoints/`) e retoma exatamente do último micro-batch processado com sucesso — sem duplicar dado, graças ao par `txnAppId`/`txnVersion` usado na escrita da camada Silver.

**Observabilidade.** Hoje, a única forma de saber se o pipeline travou é olhar o terminal. Em produção isso seria substituído por métricas expostas via Spark UI, alimentando um painel de monitoramento (Prometheus/Grafana, ou Databricks SQL Alerts) — com alerta automático se o volume de linhas processadas por minuto cair a zero.

**Governança de dados.** Os dados usados aqui são públicos (StatsBomb Open Data), sem PII. Num cenário real com dados sensíveis, a camada Bronze precisaria de controle de acesso via Unity Catalog (ou equivalente), e a camada Silver aplicaria mascaramento/anonimização antes de qualquer exposição em dashboard.

## Roadmap

- ✅ Producer + replay (Fase 1)
- ✅ Bronze → Silver → Gold streaming medallion (Fase 2)
- ✅ Dashboard ao vivo (Fase 3)
- 🔜 Catálogo de partidas (todas as ~600 disponíveis no StatsBomb open data, incluindo a carreira do Messi)
- 🔜 Tab "Player Spotlight" — análise individual por jogador (shot map, pass map, touch heatmap)
- 🔜 Visual dark-broadcast (paleta neon, fonte mono — fugindo do default Streamlit)
- 🌟 **Stretch:** camada de IA com LLM gerando comentário tático em eventos-chave

---

## Atribuição

Dados de futebol fornecidos pelo **StatsBomb** via [open-data](https://github.com/statsbomb/open-data), gratuito para pesquisa e projetos públicos. Este projeto não tem afiliação com o StatsBomb. Análises derivadas creditam o StatsBomb conforme o acordo de uso.

---

## Autor

**Guilherme Senis O. Fernandes** — Data & AI Engineer · Bauru, Brasil
[github.com/guisefe](https://github.com/guisefe) · gui.senis635@gmail.com