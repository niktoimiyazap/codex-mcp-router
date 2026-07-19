# CodexPC Connector

[English](README.md) | [Русский](README.ru.md)

> Локальный MCP-адаптер для Codex app-server с защищённым доступом к файловой системе, управляемым запуском процессов и маршрутизацией к другим MCP-серверам.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-111827)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/niktoimiyazap/codex-mcp-router/test.yml?branch=main&label=tests)](https://github.com/niktoimiyazap/codex-mcp-router/actions)

## Возможности

CodexPC Connector предоставляет MCP-клиентам контролируемый набор локальных инструментов:

- безопасное чтение и изменение файлов;
- атомарная запись UTF-8 с защитой от конфликтов;
- синхронный и фоновый запуск процессов;
- тайм-ауты, отмена, ограничение вывода и завершение дерева процессов;
- просмотр, поиск и вызов инструментов других MCP-серверов через Codex app-server;
- структурированные логи с удалением секретов и защита от запуска нескольких экземпляров.

## Архитектура

```text
MCP-клиент
    |
    v
CodexPC Connector
    |-- политика доступа к файлам и проверка UTF-8
    |-- управляемые локальные процессы
    `-- клиент JSON-RPC / JSONL
             |
             v
       codex app-server
         |-- fs/*
         |-- mcpServerStatus/list
         `-- mcpServer/tool/call
```

Коннектор запускает один долгоживущий процесс `codex app-server --stdio` и создаёт временный поток Codex для поиска и вызова MCP-инструментов.

## Требования

- Python 3.11 или новее;
- Codex CLI с поддержкой `codex app-server`;
- выполненный вход в Codex;
- настроенные в Codex MCP-серверы, если нужна дальнейшая маршрутизация.

## Быстрый старт

```bash
git clone https://github.com/niktoimiyazap/codex-mcp-router.git
cd codex-mcp-router
python -m pip install -e .
codexpc-connector
```

Запуск на Windows без установки пакета:

```bat
wrapper.cmd
```

## Интерактивный запуск туннеля

Чтобы подключить локальный MCP-сервер к уже созданному туннелю OpenAI:

```bat
launch-tunnel.cmd
```

На macOS:

```bash
chmod +x launch-tunnel.sh
./launch-tunnel.sh
```

При первом запуске мастер запрашивает данные туннеля и сохраняет Runtime API key в Windows Credential Manager или macOS Keychain. При следующих запусках ключ используется автоматически. Подробнее: [настройка туннеля](docs/TUNNEL_SETUP.md).

## Конфигурация

Скопируйте `config.example.toml` в системную папку конфигурации:

| Платформа | Путь |
|---|---|
| Windows | `%LOCALAPPDATA%\CodexPCConnector\config.toml` |
| macOS | `~/Library/Application Support/CodexPCConnector/config.toml` |
| Linux | `$XDG_STATE_HOME/codexpc-connector/config.toml` |

Минимальный пример:

```toml
workspace = "~/projects"
allowed_roots = ["~/projects"]

enable_process = false
enable_shell = false
enable_delete = true
```

Для запуска процессов требуется `enable_process=true`. Для строковых shell-команд дополнительно требуется `enable_shell=true`.

Все параметры описаны в [документации по конфигурации](docs/CONFIGURATION.md).

## Группы инструментов

### Файловая система

`read_file`, `write_file`, `list_dir`, `create_directory`, `copy_path`, `delete_path`, `download_url`, `save_uploaded_file`

Текстовые файлы по умолчанию записываются в UTF-8 атомарно. Коннектор отклоняет вероятные кракозябры и повреждения из-за устаревших кодировок.

### Процессы

`run_process`, `run_command`, `get_job`, `wait`, `list_jobs`, `cancel_job`

Состояния фоновых задач:

```text
queued, running, completed, failed, timed_out, cancelled, killed
```

### MCP-маршрутизация

`mcp_list_servers`, `mcp_list_tools`, `mcp_search_tools`, `mcp_call`

### Управление коннектором

`connector_status`, `list_active_tool_calls`, `cancel_tool_calls`

## Проверка

```bash
python -m ruff check codexpc_connector scripts tests main.py
python -m unittest discover -s tests -v
python scripts/self_check.py
python -m bandit -q -r codexpc_connector
```

Интеграционные smoke-тесты:

```bash
python scripts/smoke_processes.py
python scripts/smoke_stdio.py
```

## Документация

- [Архитектура](docs/ARCHITECTURE.md)
- [Конфигурация](docs/CONFIGURATION.md)
- [Настройка туннеля](docs/TUNNEL_SETUP.md)
- [Политика безопасности](SECURITY.md)
- [Как внести вклад](CONTRIBUTING.md)
- [Процесс релиза](docs/RELEASING.md)
- [История изменений](CHANGELOG.md)

## Безопасность

Это привилегированное локальное ПО для одного доверенного пользователя, работающее через MCP stdio. Не публикуйте его напрямую в сети. Перед включением запуска процессов или shell-команд ознакомьтесь с [SECURITY.md](SECURITY.md).

## Лицензия

MIT
