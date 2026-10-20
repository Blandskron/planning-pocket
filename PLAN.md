# Trabajo Pendiente

## Cobertura del consumer

`rooms/consumers.py` está al **67 %**, muy por debajo del resto (`services.py` al 96 %). El
umbral general de CI es 80 % y la suite está en 80,48 %, así que este archivo es lo que
sostiene el margen contra el suelo.

Lo que no está cubierto, en orden de importancia:

1. **Caminos de error del despacho.** Payload inválido, `event_type` desconocido, y una acción
   de facilitador enviada por alguien que no lo es. Debe responder un `error` estructurado
   sólo al socket que lo pidió, y no tocar a nadie más de la sala.
2. **Ciclo de conexión con varias pestañas.** `participant.joined` se emite en la primera
   pestaña y `participant.left` en la última que se cierra. `connection_count` es el contador
   que lo decide y sus bordes no tienen test.
3. **`player.moved`.** El descarte silencioso por debajo de los 110 ms y el rechazo cuando el
   recreo está cerrado.

No hace falta perseguir un número. Basta con que estos tres caminos existan como test; el
porcentaje sube solo y deja de ser el archivo que aguanta el umbral.

## El tiempo real está roto en producción

Encontrado levantando `docker compose` para revisar el rediseño. Con el `RedisChannelLayer`
real —es decir, en producción, no en los tests— **cada WebSocket muere a los ~6 s** y el cliente
reconecta en bucle. 17 desconexiones seguidas en un minuto de sala abierta:

```
ERROR Exception inside application: Timeout reading from redis:6379
redis.exceptions.TimeoutError: Timeout reading from redis:6379
WSDISCONNECT /ws/room/<id>/
```

Reproducción mínima dentro del contenedor, sin Django de por medio:

```python
pool = create_pool({"address": "redis://redis:6379/0"})     # como lo configura el proyecto
await aioredis.Redis(connection_pool=pool).bzpopmin("x", timeout=5)
# -> TimeoutError tras 5,2 s

pool = create_pool({"address": "redis://redis:6379/0", "socket_timeout": 10})
await aioredis.Redis(connection_pool=pool).bzpopmin("x", timeout=5)
# -> None tras 5,0 s, correcto
```

`channels_redis` 4.3.0 bloquea con `BZPOPMIN timeout=5` (`brpop_timeout = 5`) y no pasa
`socket_timeout`; redis-py 8.1.0 aplica al `read` un tiempo que no deja holgura sobre ese
bloqueo, así que el cliente abandona justo antes de que el servidor conteste.

El arreglo es el `socket_timeout` en `CHANNEL_LAYERS`, holgado respecto a `brpop_timeout`:

```python
"CONFIG": {"hosts": [{"address": os.environ.get('REDIS_URL'), "socket_timeout": 20}]},
```

Falta decidir si se fija ahí o se sube `brpop_timeout`, y **por qué la suite no lo vio**: los
tests corren con `InMemoryChannelLayer`, y el trabajo de CI que usa Docker sólo comprueba que la
imagen arranca. Un test que abra un socket contra un Redis real y espere más de 6 s es lo que
cierra este agujero; sin él, el siguiente salto de versión lo reabre en silencio.

## La barra inferior también dentro de la sala

El rediseño móvil dejó la barra de pestañas fuera de la sala, porque el borde inferior lo ocupa
la baraja. La sala es justo donde más se nota que no hay navegación.

**Decidido:** las dos capas se apilan, como en las apps con reproductor. La barra de pestañas se
queda fija en el borde y la mano se apoya encima de ella. Cuesta unos 60 px de mesa y votar sigue
siendo un solo toque, que es lo que no se puede perder.

Consecuencias concretas: `body.is-room .app-tabbar { display: none }` desaparece; la mano se
ancla en `bottom: var(--tabbar-height)` en vez de en `0`; el relleno inferior de `.room-shell`
pasa a ser la suma de las dos alturas, y `--deck-dock-height` se sigue midiendo —no se suma a
ojo—. El test `test_the_hand_is_docked_to_the_bottom_edge_of_a_phone` afirma hoy que la barra
**no** está visible en la sala: hay que darle la vuelta, no borrarlo.
