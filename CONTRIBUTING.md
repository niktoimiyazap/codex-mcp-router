# Contributing

1. Create a focused branch.
2. Keep tool schemas backward-compatible within a minor release.
3. Never commit credentials, local MCP configuration, logs, runtime caches, or personal paths.
4. Add or update tests for every behavior change.
5. Run:

```bash
python -m compileall -q codexpc_connector main.py
python -m ruff check codexpc_connector scripts tests main.py
python -m bandit -q -r codexpc_connector
python -m unittest discover -s tests -v
python scripts/self_check.py
python -m pip_audit -r audit-requirements.txt --progress-spinner off
```

Changes involving file authorization, process execution, network transports, credential handling, or logging require explicit security review.
