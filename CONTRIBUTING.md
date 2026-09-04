# Cómo contribuir a Planning Pocket

## El flujo: GitHub Flow

`main` siempre está desplegable. No hay ramas `develop`, `release` ni `hotfix`, y no hay
versiones vivas en paralelo. Todo lo demás sale de una regla corta:

1. Ramifica desde `main`. Nombra la rama por lo que hace: `feat/recreo-movil`,
   `fix/voto-fantasma-al-reconectar`.
2. Commitea en unidades coherentes. Un commit que hay que explicar con "y además" son dos.
3. Abre un pull request en cuanto tengas algo que enseñar, aunque esté a medias. Márcalo como
   borrador si aún no se puede revisar.
4. CI tiene que estar en verde. No es negociable ni se salta con `--no-verify`.
5. Revisión de una persona, y `main` se actualiza con *squash merge*.
6. Desplegar viene después del merge, no antes.

### Convención de mensajes

[Conventional Commits](https://www.conventionalcommits.org/es/), en español:

```
feat(mesa): repartir las cartas desde el centro del paño
fix(websocket): no perder el voto propio al reconectar en móvil
test(e2e): cubrir el recreo con dos personas
docs(adr): registrar por qué el recreo se cierra solo al revelar
chore(deps): subir Django a 6.1.1
```

El asunto describe el cambio, no el archivo. El cuerpo explica **por qué**, porque el qué ya
está en el diff.

## Antes de abrir el pull request

```bash
python -m ruff check .
python -m pytest .
python manage.py check
python manage.py makemigrations --check --dry-run
```

Y si tocaste la mesa, la baraja, el reveal o cualquier cosa que se dibuje:

```bash
python -m playwright install chromium   # sólo la primera vez
DJANGO_ALLOW_ASYNC_UNSAFE=true python -m pytest -m e2e
```

En PowerShell la última línea es
`$env:DJANGO_ALLOW_ASYNC_UNSAFE = "true"; python -m pytest -m e2e`.

Cobertura: el umbral de CI es 80 % general y la suite está en 80,48 %. El margen es estrecho
a propósito. Si tu cambio la baja, añade los tests en el mismo pull request.

```bash
python -m pytest . --cov --cov-report=term-missing
```

## Reglas que no se negocian

Estas no están abiertas a discusión dentro de un pull request. Si crees que una debería
cambiar, ábrele un issue y quedará como un ADR nuevo en `docs/DECISIONS.md`.

- **El servidor es la autoridad.** El navegador manda intenciones; `rooms/services.py`
  decide. Una regla de negocio en el consumer o en el cliente es un bug, aunque funcione.
- **El voto es privado hasta el reveal.** Ningún payload lleva el voto de otra persona antes
  de que el facilitador revele. Hay tests que lo comprueban con igualdad exacta del payload;
  si te estorban, el problema es el cambio.
- **Sin frameworks SPA.** HTML, CSS y JavaScript nativos. React o Vue entran sólo con un ADR
  aceptado, no con un pull request.
- **Sin dependencias sin justificar.** Si añades una, el pull request explica qué no se puede
  hacer sin ella.
- **Sin archivos de historial.** Nada de `progress.md` ni `conversations.md`. Git es el
  historial.

Los agentes de IA tienen además su propio contrato en [`AGENTS.md`](AGENTS.md).

## Publicar una versión

Sólo con permisos de escritura en el repositorio.

1. Actualiza `CHANGELOG.md`: mueve lo que hay bajo `## [Sin publicar]` a una sección
   `## [X.Y.Z] - AAAA-MM-DD` y añade el enlace de comparación al final.
2. Sube `version` en `pyproject.toml` al mismo número. El workflow de release compara ambos y
   falla si no coinciden.
3. Merge a `main` y espera a que CI esté verde.
4. Tag anotado y push:

   ```bash
   git tag -a v1.2.0 -m "Planning Pocket v1.2.0"
   git push origin v1.2.0
   ```

`.github/workflows/release.yml` corre el CI completo otra vez sobre el tag, verifica que el
tag, `pyproject.toml` y el `CHANGELOG.md` dicen lo mismo, y publica la GitHub Release con las
notas del changelog. Un tag por sí solo no publica nada si el CI falla.

Números: `MAYOR` cuando rompes el protocolo WebSocket o la configuración de despliegue,
`MENOR` cuando añades algo, `PARCHE` para arreglos.

## Proteger `main`

La protección de rama es un ajuste del repositorio, no un archivo, así que no viaja en el
repo. La configuración que corresponde a este flujo, en *Settings → Branches → main*:

- Require a pull request before merging (1 aprobación)
- Require status checks to pass → **`CI`** (el job agregador de `ci.yml`; apuntar a ese en
  vez de a los cinco jobs evita tener que mantener la lista a mano)
- Require branches to be up to date before merging
- Require conversation resolution before merging
- Block force pushes

## Reportar un fallo de seguridad

No abras un issue. Ver [`SECURITY.md`](SECURITY.md).
