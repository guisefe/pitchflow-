.PHONY: help up down logs download replay test lint clean

help:
	@echo "pitchpulse — real-time football match-event lakehouse"
	@echo ""
	@echo "  make up        Start Redpanda + console (UI: http://localhost:8080)"
	@echo "  make down      Stop the cluster"
	@echo "  make download  Cache the configured match from StatsBomb open-data"
	@echo "  make replay    Stream the match into Kafka in match-clock order"
	@echo "  make test      Run the test suite"
	@echo "  make logs      Tail Redpanda logs"
	@echo "  make clean     Stop everything and clear cached data"

up:
	docker compose up -d
	@echo "Console UI: http://localhost:8080"

down:
	docker compose down

logs:
	docker compose logs -f redpanda

download:
	python -m producer.download

replay:
	python -m producer.replay

test:
	python -m pytest producer/tests/ -v --cov=producer --cov-report=term-missing

clean:
	docker compose down -v
	rm -f data/events_*.json

.PHONY: bronze peek
bronze:
	python -m streaming.bronze

peek:
	python -m streaming.peek

.PHONY: silver test
silver:
	python -m streaming.silver

test:
	python -m pytest streaming/tests/ producer/tests/ -v --tb=short

.PHONY: gold
gold:
	python -m streaming.gold
