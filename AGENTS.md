# Contrato para Agentes de IA

Bienvenido a **Planning Pocket**. Este repositorio sigue una filosofía *Agents-first* y *Human-friendly*. Como agente de IA, debes seguir estrictamente estas reglas.

## 1. Reglas de Arranque

Antes de modificar cualquier código en una nueva sesión, DEBES leer los siguientes archivos en este orden:
1. `AGENTS.md` (Este archivo)
2. `PLAN.md` (Contiene exclusivamente el trabajo pendiente)
3. `docs/ARCHITECTURE.md` (Contexto arquitectónico)
4. `docs/PRODUCT.md` (Reglas de producto y diseño)

NO leas todo el repositorio de forma indiscriminada.
NO intentes construir toda la aplicación de una sola vez. Trabaja UNA FASE A LA VEZ.

## 2. Flujo de Trabajo

En cada iteración:
1. Identifica la siguiente tarea pendiente en `PLAN.md`.
2. Implementa una unidad coherente de trabajo (código, tests, documentación).
3. Verifica tu trabajo (ejecuta tests y linting).
4. Cuando una tarea esté completamente terminada y validada, **ELIMÍNALA** de `PLAN.md`. NO la marques con `[x]`, bórrala.
5. Detente y reporta al usuario con un resumen breve de la iteración.

## 3. Reglas Arquitectónicas y de Desarrollo

- **Simplicidad ante todo**: Elige la opción que mantenga el sistema simple, testeable y fácil de entender.
- **Stack**: Python + Django, PostgreSQL, Redis, Django Channels (WebSockets), HTMX/Alpine (solo si es necesario), HTML/CSS/JS nativo. NO usar frameworks SPA (React, Vue, etc.) a menos que esté documentado en `DECISIONS.md`.
- **Servidor como fuente de verdad**: El backend (Django) decide las validaciones de negocio. El navegador no es la autoridad.
- **Privacidad de Votos**: Crítico. Antes del "reveal", los votos deben ser privados y no enviarse a clientes no autorizados.

## 4. Testing

- Aplica la pirámide de tests: Unit tests (dominio, servicios), Integration tests (ORM, views, websockets), E2E (Playwright para flujos críticos).
- Cobertura esperada: Dominio/Servicios 90%+, General 80%+.
- Test-First en reglas críticas: `cast_vote`, `reveal_round`, `reset_round`, `guest identity`, `authorization`.

## 5. Qué NO hacer

- NO crees archivos históricos de logs o progresos (`conversations.md`, `history.md`, etc.). Git es el historial.
- NO dejes tareas marcadas como terminadas en `PLAN.md`.
- NO optimices para demostrar complejidad técnica.
- NO agregues dependencias sin justificación.

## 6. Verificación y CI

Antes de decir que una tarea está terminada:

```bash
python -m ruff check .
python -m pytest .              # 96 tests, unos 5 segundos
python manage.py check
python manage.py makemigrations --check --dry-run
```

Si tocaste algo que se dibuja en la mesa, además los tests de navegador
(`DJANGO_ALLOW_ASYNC_UNSAFE=true pytest -m e2e`).

`.github/workflows/ci.yml` corre todo eso más `check --deploy` con la configuración real de
producción, el umbral de cobertura (80 %) y el arranque de la imagen Docker. No inventes un
comando de verificación distinto: si CI lo corre, córrelo tú igual.

El flujo de ramas, commits y publicación de versiones está en `CONTRIBUTING.md`.

## 7. Cuándo detenerse

Al finalizar una unidad lógica y verificable, o al finalizar la fase actual. Nunca avances por cinco o diez fases de forma automática.
