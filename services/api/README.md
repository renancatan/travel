# API Service

Planned home for the main backend service.

Expected responsibilities:

- trip and album APIs
- media metadata APIs
- selection and approval flows
- map entry creation and updates
- job dispatching to workers
- LLM orchestration for captions and categorization

Current direction:

- likely `FastAPI`
- service should stay thin and delegate heavy work to background jobs

Current local smoke-test entrypoint:

- [app/main.py](/home/renancatan/renan/projects/travel/services/api/app/main.py)

Run locally:

```bash
cd /home/renancatan/renan/projects/travel
./scripts/run_api_dev.sh
```
