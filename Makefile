# Makefile for Speech Task Project

.PHONY: help build up down logs test lint format clean \
        logs-tts logs-asr logs-gateway test-client health

# Default target
help:
	@echo "Available commands:"
	@echo "  build         - Build Docker images"
	@echo "  up            - Start all services"
	@echo "  down          - Stop all services"
	@echo "  logs          - Show logs for all services"
	@echo "  test          - Run unit tests"
	@echo "  lint          - Run code linting"
	@echo "  format        - Format code"
	@echo "  clean         - Clean up containers and volumes"
	@echo "  logs-tts      - Show TTS service logs"
	@echo "  logs-asr      - Show ASR service logs"
	@echo "  logs-gateway  - Show Gateway service logs"
	@echo "  test-client   - Run client TTS/ASR test"
	@echo "  health        - Check service health"

# Docker commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

# Development commands
test:
	pytest -v

lint:
	ruff check .
	black --check .

format:
	black .
	ruff check --fix .

# Cleanup
clean:
	docker-compose down -v
	docker system prune -f

# Service-specific logs
logs-tts:
	docker-compose logs -f tts

logs-asr:
	docker-compose logs -f asr

logs-gateway:
	docker-compose logs -f gateway

# Client testing
test-client:
	@echo "Running end-to-end test via Gateway..."

	@echo "-> Sending text to Gateway TTS..."
	python3 client/stream_tts.py \
		--text "Hello world" \
		--out test_output.wav \
		--uri ws://localhost:8000/ws/tts

	@echo "TTS completed. Output saved to test_output.wav"

	@echo "-> Sending generated WAV back to Gateway for ASR..."
	python3 client/echo_bytes.py \
		--wav test_output.wav \
		--out test_echo.wav \
		--url http://localhost:8000/api/echo-bytes

	@echo "ASR completed. Output saved to test_echo.wav"

	@echo "End-to-end Gateway test finished successfully."

# Health checks
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8082/healthz || echo "TTS service not responding"
	@curl -s http://localhost:8081/healthz || echo "ASR service not responding"
	@curl -s http://localhost:8000/healthz || echo "Gateway service not responding"
