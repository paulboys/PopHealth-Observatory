# Logging

PopHealth Observatory uses a centralized package logger configured in `pophealth_observatory.logging_config`.

## Default Behavior

- Logger name: `pophealth_observatory`
- Default level: `INFO`
- Format: `timestamp level=... logger=... message=...`
- Logger propagation to root is disabled to avoid duplicate handlers in notebooks/apps.

## Set Log Level

Use the `LOGLEVEL` environment variable before running your script or app.

### PowerShell

```powershell
$env:LOGLEVEL = "DEBUG"
python -c "import pophealth_observatory as p; print(p.__version__)"
```

### Bash

```bash
export LOGLEVEL=DEBUG
python -c "import pophealth_observatory as p; print(p.__version__)"
```

Supported levels follow Python logging names (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).
Invalid values fall back to `INFO`.

## Transitional Fallback Prints

During logging migration, many internal call sites use `log_with_fallback(...)`.
That helper logs via the package logger and mirrors messages to stdout for compatibility.

- This duplication is intentional during migration.
- Removal timeline for compatibility-related transitions is documented in `docs/versioning.md`.

For your own extension code, prefer direct logger calls unless you explicitly need mirrored stdout:

```python
import logging

logger = logging.getLogger("pophealth_observatory")
logger.info("Custom message")
```

## Recommended Usage in Applications

```python
import logging
from pophealth_observatory.logging_config import configure_logging

configure_logging()  # Reads LOGLEVEL from environment if set
logger = logging.getLogger("pophealth_observatory")
logger.info("Application started")
```
