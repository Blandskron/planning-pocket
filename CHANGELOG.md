# Changelog

Todas las novedades relevantes de Planning Pocket, en formato
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
El proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [1.0.0] - 2026-09-03

Primera versión publicada. La aplicación ya estaba completa; lo que faltaba era poder
llamarla por su nombre y validar cada cambio antes de que llegue a `main`.

### Añadido

- **La mesa.** Los asientos se colocan sobre un anillo elíptico calculado a partir de cuánta
  gente hay, el paño informa de la ronda, la baraja es una mano en abanico y el reveal tiene
  cuenta atrás y volteo escalonado. Cada persona se ve a sí misma al frente.
- **Identidad por persona.** Cara, mascota y color, elegidos al entrar o desde la sala, y
  derivados de un hash estable en cualquier otro caso. La mascota refleja el estado de su
  dueño con lenguaje corporal.
- **Capa de juego.** Cualquiera puede lanzar un objeto blando a otra persona de la mesa, y el
  facilitador puede abrir un recreo donde la gente se levanta mientras se espera el último
  voto. Son cosméticos, el servidor pone los límites, y se apagan por sala o por pantalla.
  Las reglas que impiden que se convierta en presión están en `docs/DECISIONS.md`, ADR-005.
- **Privacidad del voto garantizada por el servidor.** Ningún valor de voto sale hacia otro
  cliente hasta que el facilitador revela. La única excepción es el propio voto de cada
  persona, para poder restaurar su carta al reconectar.
- **Facilitador e invitados.** Sólo quien crea la sala necesita cuenta. El resto entra con un
  enlace y un nombre.
- **Cola de historias.** El facilitador enfoca una historia, guarda la estimación y pasa a la
  siguiente sin recargar.
- **Tiempo real con Django Channels.** Participantes, estado de voto, cambio de historia y
  reveal se propagan por WebSocket. Redis en producción, capa en memoria en local.
- **Sonido.** Cinco tonos sintetizados en el navegador, apagados por defecto.
- **Despliegue.** `Dockerfile` y `docker-compose.yml` con PostgreSQL y Redis. HSTS, cookies
  seguras, redirección HTTPS y `SECRET_KEY` obligatoria en cuanto `DJANGO_DEBUG` es falso.
- **Integración continua.** GitHub Actions valida cada pull request: ruff, la suite completa
  con umbral de cobertura, los tests de navegador, `check --deploy` con la configuración
  real de producción, y que la imagen Docker arranque. Un tag `vX.Y.Z` publica la release
  sólo después de pasar el mismo CI.
- **Documentación de contribución.** `CONTRIBUTING.md` con el flujo de trabajo (GitHub Flow)
  y `SECURITY.md` con cómo reportar un fallo sin publicarlo.

### Cambiado

- **La suite pasó de 8 min 30 s a 5 segundos.** Los tests usaban el hasher de contraseñas de
  producción; cada inicio de sesión costaba unos nueve segundos de PBKDF2. `settings_test`
  ahora usa MD5, que no es una decisión de seguridad —nada de esa base de datos sobrevive a
  la corrida— sino lo que hace que la suite quepa en CI.
- Suelo de Python declarado como 3.12, que es lo que Django 6.1 exige de verdad. `pyproject`
  y el README decían 3.11.

### Eliminado

- La app `poker`, que estaba en `INSTALLED_APPS` sin una sola línea de código. Las reglas de
  negocio viven en `rooms/services.py`.
- `djangorestframework`, que estaba instalado y declarado sin ningún uso: no hay
  serializadores, vistas ni rutas de DRF en el proyecto.

[Sin publicar]: https://github.com/Blandskron/planning-pocket/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Blandskron/planning-pocket/releases/tag/v1.0.0
