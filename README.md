Вот простой и лаконичный вариант README для твоего проекта:

````markdown
# Speech TTS + STT Server

Проект реализует стриминговый TTS (Text-to-Speech) и оффлайн STT (Speech-to-Text) с помощью Python, FastAPI и Docker.  

---

## Сервисы

1. **TTS** — синтез речи с потоковой отдачей PCM.  
2. **STT** — распознавание речи с готового файла (PCM).  
3. **Gateway** — проксирует запросы TTS и ASR, объединяет поток.  

---

## Установка и запуск

```bash
git clone <repo-url>
cd asr_tts_server
cp env.example .env
make build
make up
````

Проверка логов:

```bash
make logs
```

Остановка сервисов:

```bash
make down
```

---

## Клиент

Примеры работы клиента:

```bash
make test-client
```

* `stream_tts.py` — отправляет текст на TTS → сохраняет PCM → WAV.
* `echo_bytes.py` — отправляет WAV на Gateway → получает распознанный текст и PCM.

---

## Тесты

```bash
make test
```

---

## Линт и форматирование

```bash
make lint   # проверка
make format # автоформатирование
```

---

## Очистка

```bash
make clean
```