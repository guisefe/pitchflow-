# pitchflow

> **Streaming de eventos de partida de futebol em um lakehouse Delta em tempo real.**

Replica dados reais do StatsBomb como um stream Kafka ao vivo, processa com Spark Structured Streaming em um medallion Bronze→Silver→Gold, e serve analytics ao vivo — corrida de xG, mapa de chutes, momentum, win probability — num dashboard Streamlit que atualiza a cada 3 segundos.

**100% open-source. Roda local ou no GitHub Codespaces. Zero custo de dados.**

![CI](https://github.com/guisefe/pitchflow/actions/workflows/ci.yml/badge.svg)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/guisefe/pitchflow)

---

## Por que este projeto existe

### Por que streaming

Quase todo portfólio de engenharia de dados é batch — jobs agendados sobre tabelas finitas. Streaming é a skill que separa o nível pleno do sênior, e é a mais demandada justamente porque é mais difícil: o dado nunca para de chegar, então você precisa raciocinar sobre *quando* é "agora", o que fazer com eventos que chegam atrasados, e como manter totais acumulados sem reler tudo. `pitchflow` existe pra provar essa skill de ponta a ponta.

### Por que futebol e por que StatsBomb

Um projeto de portfólio aterra melhor quando o domínio é real e o autor claramente se importa. O StatsBomb publica [dados de evento profissionais e gratuitos](https://github.com/statsbomb/open-data) — cada passe, conduç̃ao e chute, com o valor de expected goals (xG) e coordenadas do campo. É o dataset que a comunidade séria de football analytics usa de verdade.

### Por que event replay

Feeds de eventos ao vivo são pagos. Em vez de pagar, o `pitchflow` *replica* uma partida real em ordem de relógio de jogo, a velocidade configurável — um jogo de 90 minutos streama em ~90 segundos. Isso não é um workaround: replay é um padrão de produção real (é assim que você faz backfill e reprocessa dados históricos por um sistema de streaming), e torna o pipeline **determinístico e reproduzível**.

### Por que streaming medallion

O medallion Bronze→Silver→Gold é o padrão comprovado de lakehouse usado em produção no Databricks. O `pitchflow` aplica essa *mesma* estrutura a um stream contínuo em vez de uma tabela batch — reutilizando uma arquitetura que escala enquanto demonstra sua forma mais difícil, a de streaming.

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
                             │  Bronze  JSON cru (append, exactly-once)     │
                             │     │    streaming/bronze.py                  │
                             │     ▼                                         │
                             │  Silver  colunas tipadas + dedup + watermark  │
                             │     │    streaming/silver.py                  │
                             │     ▼                                         │
                             │  Gold    métricas ao vivo (MERGE upsert)     │
                             │          streaming/gold.py                    │
                             │   • xg_timeline   corrida de xG por minuto   │
                             │   • match_state   placar + win probability    │
                             │   • shots         mapa de chutes              │
                             │   • momentum      dominância nos últimos 5min │
                             └───────────────────────┬──────────────────────┘
                                                     │  Delta Lake (ACID)
                             ┌───────────────────────▼──────────────────────┐
                             │  Streamlit live dashboard (dashboard/app.py)  │
                             │  auto-refresh a cada 3s · lê via deltalake   │
                             └──────────────────────────────────────────────┘
```

---

## Stack

| Camada | Ferramenta | Versão | Por quê |
|--------|-----------|--------|---------|
| Event log | **Redpanda** (API Kafka) | 24.1.x | Binário único, sem ZooKeeper, RAM baixa — semântica Kafka sem o peso operacional |
| Kafka client | **confluent-kafka** | 2.4.0 | Cliente Python padrão de produção |
| Stream processing | **Spark Structured Streaming** | 3.5.1 | Padrão de mercado, espelha o Databricks do dia a dia; watermarking + agregação stateful nativos |
| Formato de tabela | **Delta Lake** | 3.2.0 | ACID, sink idempotente, time travel — o padrão de lakehouse |
| Leitura no dashboard | **deltalake** (Python) | 0.18.x | Lê tabelas Delta sem Spark — rápido e leve para serving |
| Dashboard | **Streamlit** + **Plotly** | 1.35 / 5.22 | Rápido de construir, auto-refresh, demoável ao vivo |
| Containerização | **Docker Compose** | — | Um comando para subir tudo |
| CI | **GitHub Actions** | — | Testes em todo push; badge verde |
| Dados | **StatsBomb Open Data** | — | Gratuito, real, profissional, com xG e coordenadas |

---

## Quickstart

### Opção 1 — GitHub Codespaces (recomendado)

Clica em **Open in Codespaces** acima. O ambiente monta sozinho com Python, Docker e dependências instaladas.

> **Gestão de cota:** a stack pesada (Spark + Kafka) usa uma máquina de 4-core (≈30h grátis/mês). Para trabalho leve (testes, edição) escolha 2-core. **Sempre delete** o Codespace ao terminar — parado ainda consome storage da cota.

### Opção 2 — Local

```bash
git clone https://github.com/guisefe/pitchflow.git
cd pitchflow

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Java 17 é obrigatório para o Spark
sudo apt-get install -y openjdk-17-jdk-headless           # Linux/Codespaces
# brew install openjdk@17                                 # macOS

cp .env.example .env
```

---

## Como rodar o pipeline completo

Você precisa de **5 terminais** abertos ao mesmo tempo (ou use `tmux`).

```bash
# Terminal 1 — infraestrutura
make up

# Terminal 2 — Bronze: Kafka → Delta (fica rodando)
make bronze

# Terminal 3 — Silver: Bronze → tipado + deduplicado (fica rodando)
make silver

# Terminal 4 — Gold: Silver → métricas ao vivo (fica rodando)
make gold

# Terminal 5 — replay + dashboard
make download   # cacheia a final Argentina x França (uma vez só)
make replay     # streama os 4.407 eventos em ~2.6 min
make dashboard  # abre em localhost:8501
```

Abre **localhost:8501** e assiste a final se desenrolar em tempo real.

Para ver os dados direto no Delta sem subir o dashboard:
```bash
make peek                              # Bronze
make peek data/delta/silver/events     # Silver
make peek data/delta/gold/match_state  # Gold
```

---

## Testes

```bash
make test      # 28 testes, roda em < 1s, sem broker, sem Spark
```

A lógica pura (relógio do jogo, classificação de eventos, xG, win probability) é testada isolada de qualquer infraestrutura. O producer é testado com um producer falso. A CI roda esses mesmos testes em todo push.

---

## Conceitos de streaming no código

| Conceito | Onde aparece | Por quê importa |
|----------|-------------|-----------------|
| **Event replay** | `producer/replay.py` | Substitui dados ao vivo pagos; pattern real de backfill |
| **Checkpoint** | `streaming/bronze.py` | O job recomeça exatamente onde parou — sem perda ou duplicação |
| **Watermark** | `streaming/silver.py` | Limita o estado de dedup em memória; sem ele o estado cresce pra sempre |
| **Dedup stateful** | `streaming/silver.py` | `dropDuplicates(["event_id"])` com watermark — exactly-once no Silver |
| **Idempotência Delta** | `streaming/silver.py` | `txnAppId + txnVersion` — replay do mesmo batch_id é no-op |
| **foreachBatch + MERGE** | `streaming/gold.py` | Único jeito de fazer upsert em streaming com Delta |
| **Running state** | `streaming/gold.py` | xG acumula por time/minuto sem reler tudo (o coração do streaming) |
| **Sliding window** | `streaming/gold.py` | Momentum olha só os últimos 5 min — diferente do xG que é cumulativo |
| **cache() / unpersist()** | `streaming/gold.py` | O mesmo batch é lido 4x — cache evita re-scan do Delta 4 vezes |

---

## Estrutura do repositório

```
pitchflow/
├── producer/               # Fase 1 — replay producer
│   ├── config.py           # variáveis de ambiente
│   ├── download.py         # download + cache StatsBomb
│   ├── replay.py           # lógica de replay (pura, testável)
│   └── tests/
├── streaming/              # Fase 2 — Spark Structured Streaming
│   ├── session.py          # fábrica da SparkSession (Delta + Kafka)
│   ├── config.py           # caminhos das tabelas e checkpoints
│   ├── bronze.py           # Kafka → Bronze Delta (append)
│   ├── silver.py           # Bronze → Silver (parse + dedup + watermark)
│   ├── gold.py             # Silver → Gold (4 métricas via MERGE)
│   ├── metrics.py          # funções puras: xG, momentum, win prob
│   ├── peek.py             # inspetor rápido de tabelas Delta
│   └── tests/
├── dashboard/
│   └── app.py              # Streamlit live dashboard
├── docs/
│   └── PROJECT.md          # spec completa: requisitos, riscos, decisões
├── docker-compose.yml      # Redpanda + console
├── Makefile                # todos os comandos do projeto
└── .devcontainer/          # Codespaces one-click
```

---

## Variáveis de ambiente

| Variável | Padrão | Significado |
|----------|--------|-------------|
| `MATCH_ID` | `3869685` | Partida StatsBomb (padrão: Final da Copa 2022) |
| `REPLAY_SPEED` | `60` | Multiplicador de velocidade (60 = 90min em ~90s) |
| `MAX_SLEEP_SECONDS` | `3` | Teto de espera entre eventos (limita pausas do intervalo) |
| `KAFKA_BROKER` | `localhost:19092` | Endereço do Redpanda |
| `MATCH_TOPIC` | `match.events` | Tópico Kafka de destino |

---

## Atribuição de dados

Os dados de futebol são fornecidos pelo **StatsBomb** via [open-data](https://github.com/statsbomb/open-data), gratuito para uso em pesquisa e projetos públicos. Este projeto não tem afiliação com o StatsBomb. Conforme o acordo de uso, qualquer análise derivada desses dados credita o StatsBomb como fonte.

---

## Autor

**Guilherme Senis** — Data & AI Engineer
[github.com/guisefe](https://github.com/guisefe) · gui.senis635@gmail.com