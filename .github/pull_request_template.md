## Qué cambia

<!-- Una unidad coherente de trabajo. Si necesitas viñetas para varios temas sin relación,
     probablemente sean varios pull requests. -->

## Por qué

<!-- El problema, no la solución. La solución ya está en el diff. -->

## Cómo lo verificaste

- [ ] `python -m pytest .`
- [ ] `python -m ruff check .`
- [ ] `python manage.py check`
- [ ] Tests de navegador si tocaste la mesa: `DJANGO_ALLOW_ASYNC_UNSAFE=true pytest -m e2e`

## Checklist

- [ ] Si cambié reglas de negocio, están en `rooms/services.py` y no en el consumer ni en el cliente
- [ ] Si cambié el protocolo WebSocket, actualicé `docs/ARCHITECTURE.md`
- [ ] Si tomé una decisión que costará revertir, la registré en `docs/DECISIONS.md`
- [ ] Si añadí una dependencia, expliqué arriba por qué no se puede sin ella
- [ ] Ningún voto sale al cliente antes del reveal
