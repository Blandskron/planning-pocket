# Política de seguridad

## Versiones con soporte

| Versión | Soporte |
| ------- | ------- |
| 1.0.x   | Sí      |
| < 1.0   | No      |

Sólo la última versión menor recibe arreglos. No hay ramas de mantenimiento.

## Cómo reportar

**No abras un issue público.** Usa
[Report a vulnerability](https://github.com/Blandskron/planning-pocket/security/advisories/new),
que es privado hasta que haya un arreglo.

Ayuda mucho incluir:

- Qué rompe, en una frase.
- Cómo reproducirlo. Un `curl` o unos frames de WebSocket valen más que una descripción.
- Qué consigue quien lo explota: leer votos ajenos antes del reveal, actuar como facilitador
  sin serlo, entrar en una sala que no es suya, ejecutar algo en el navegador de otra
  persona.
- La versión o el commit.

Respondemos en un plazo de 5 días hábiles con si lo reproducimos y un plazo estimado. Si el
fallo es real, el aviso se publica junto con el arreglo, con crédito salvo que prefieras
quedar anónimo.

## Lo que consideramos vulnerabilidad

El modelo de amenazas de este proyecto gira alrededor de una idea: **una sala es una reunión,
y lo único que de verdad hay que proteger dentro es el voto antes del reveal.**

Cuenta como vulnerabilidad:

- Leer el voto de otra persona antes de que el facilitador revele, por WebSocket, por HTTP o
  por cualquier otra vía.
- Ejecutar una acción de facilitador (revelar, reiniciar, activar historia, guardar
  estimación, abrir recreo, apagar la capa de juego) sin ser el dueño de la sala.
- Suplantar la identidad de otro participante, o cambiar la apariencia del asiento ajeno.
- Acceder a una sala sin conocer su `public_id`, o enumerarlos.
- XSS a través de nombres de invitado, títulos o descripciones de historias.
- Cualquier cosa que evada `AllowedHostsOriginValidator` en el handshake del WebSocket.

No cuenta:

- Que quien tenga el enlace pueda entrar. Es el diseño: el `public_id` **es** la credencial
  (ver ADR-004 en `docs/DECISIONS.md`).
- Que el facilitador vea cosas que los invitados no. También es el diseño.
- Resultados de escáneres sin un impacto demostrable.
- Ausencia de rate limiting en la capa de juego más allá de los límites que ya aplica
  `rooms/services.py`, salvo que muestres cómo degrada la sala.
- Despliegues mal configurados por terceros (`DEBUG=True` en producción, `SECRET_KEY`
  filtrada, Redis abierto a internet). El proyecto obliga a configurarlo bien —
  `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS` son obligatorias con `DJANGO_DEBUG=False` —
  pero no puede impedir que alguien las ponga mal.

Las mitigaciones concretas y dónde vive cada una están en
[`docs/SECURITY.md`](docs/SECURITY.md).
