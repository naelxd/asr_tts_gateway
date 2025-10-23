# Speech TTS + STT Server

Высокопроизводительный микросервисный пайплайн для стримингового синтеза речи (TTS) и распознавания речи (STT) с использованием современных open-source моделей.

## Возможности

- **Стриминговый TTS**: Real-time синтез речи с потоковой отдачей PCM
- **Offline STT**: Распознавание речи по аудиофайлам с временными метками
- **Микросервисная архитектура**: 3 независимых сервиса + Gateway
- **WebSocket API**: Двунаправленная связь для real-time приложений
- **Docker-ready**: Полная контейнеризация с docker-compose
- **Production-ready**: Структурированное логирование, health checks, unit тесты

## Архитектура

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │   Gateway   │    │ TTS Service │
│             │◄──►│             │◄──►│             │
│ stream_tts  │    │   :8000     │    │   :8082     │
│ echo_bytes  │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ ASR Service │
                   │   :8081     │
                   │             │
                   └─────────────┘
```

### Сервисы

- **TTS Service** (`:8082`): Coqui TTS + Tacotron2-DDC для синтеза речи
- **ASR Service** (`:8081`): Faster-Whisper + Tiny.en для распознавания речи  
- **Gateway** (`:8000`): Единая точка входа, проксирование запросов
- **Client**: Примеры использования для тестирования

## 🛠️ Технологии

- **Backend**: Python 3.10 + FastAPI + WebSocket
- **TTS**: Coqui TTS с моделью Tacotron2-DDC
- **ASR**: Faster-Whisper с моделью Tiny.en
- **Containerization**: Docker + Docker Compose
- **Testing**: pytest + FastAPI TestClient
- **Code Quality**: ruff + black + mypy
- **Logging**: JSON структурированные логи

## Быстрый старт

### Предварительные требования

- Docker & Docker Compose
- Python 3.10+ (для локальной разработки)
- 4GB+ RAM (для загрузки моделей)

### Установка

```bash
# Клонирование репозитория
git clone https://github.com/naelxd/asr_tts_gateway.git
cd asr_tts_gateway

# Копирование конфигурации
cp env.example .env

# Сборка и запуск сервисов
make build
make up
```

### Проверка работоспособности

```bash
# Проверка health checks
make health

# Просмотр логов
make logs

# End-to-end тест
make test-client
```

## API Документация

### TTS Service (WebSocket)

**Эндпоинт**: `ws://localhost:8082/ws/tts`

**Запрос**:
```json
{"text": "Hello world"}
```

**Ответ**: Поток PCM чанков + `{"type": "end"}`

### ASR Service (HTTP)

**Эндпоинт**: `POST /api/stt/bytes?sr=16000&ch=1&lang=en`

**Запрос**: Raw PCM данные (s16le mono 16kHz)

**Ответ**:
```json
{
  "text": "recognized text",
  "segments": [
    {"start_ms": 0, "end_ms": 1200, "text": "Hello"}
  ]
}
```

### Gateway (Unified API)

**TTS WebSocket**: `ws://localhost:8000/ws/tts`
**ASR HTTP**: `POST /api/echo-bytes?sr=16000&ch=1&fmt=s16le`

## Тестирование

### Unit тесты

```bash
# Запуск всех тестов
make test

# Тесты конкретного сервиса
pytest asr_service/tests/
pytest tts_service/tests/
pytest gateway/tests/
```

### End-to-end тесты

```bash
# Полный цикл TTS → ASR
make test-client
```

### Клиентские примеры

```bash
# TTS тест
python client/stream_tts.py \
  --text "Hello world" \
  --out output.wav \
  --uri ws://localhost:8000/ws/tts

# ASR тест  
python client/echo_bytes.py \
  --wav input.wav \
  --out output.wav \
  --url http://localhost:8000/api/echo-bytes
```

## Мониторинг

### Логи

```bash
# Все сервисы
make logs

# Конкретный сервис
make logs-tts
make logs-asr  
make logs-gateway
```

### Health Checks

```bash
# Проверка состояния
curl http://localhost:8082/healthz  # TTS
curl http://localhost:8081/healthz  # ASR
curl http://localhost:8000/healthz   # Gateway
```

## Разработка


### Code Quality

```bash
# Линтинг
make lint

# Форматирование
make format

```

### Структура проекта

```
├── asr_service/          # ASR микросервис
│   ├── app/main.py      # FastAPI приложение
│   ├── tests/           # Unit тесты
│   └── Dockerfile       # Docker образ
├── tts_service/         # TTS микросервис
│   ├── app/main.py      # FastAPI приложение
│   ├── tests/           # Unit тесты
│   └── Dockerfile       # Docker образ
├── gateway/             # Gateway сервис
│   ├── app/main.py      # FastAPI приложение
│   ├── tests/           # Unit тесты
│   └── Dockerfile       # Docker образ
├── client/              # Клиентские примеры
├── common/              # Общие утилиты
├── docker-compose.yml   # Docker Compose конфигурация
├── Makefile            # Автоматизация команд
└── pyproject.toml      # Конфигурация проекта
```