# Registro de Decisiones Arquitectónicas (ADR)

Este documento registra decisiones técnicas y de diseño importantes que impactan a Planning Pocket.

---

## ADR-001 — Django como framework central

**Estado:** Aceptado

**Decisión:** Utilizar Python con Django como el entorno principal para construir el producto, y renderizar el frontend inicial con Django Templates. No crear una SPA de inmediato.

**Motivo:** Queremos mantener el proyecto simple, rápido de iterar y reducir la complejidad del ciclo de CI/CD. Django nos proporciona autenticación, ORM seguro, sesiones de manera inmediata, eliminando la fricción de manejar CORS, tokens JWT y APIs REST para operaciones triviales iniciales.

**Consecuencias:**
- La experiencia inicial podría parecer tradicional, pero se compensará con interactividad incremental (WebSockets/HTMX).
- Mayor dependencia en la redención de plantillas en el servidor.

---

## ADR-002 — Django Channels y Redis para tiempo real

**Estado:** Aceptado

**Decisión:** Adoptar WebSockets mediante Django Channels y usar Redis como capa base.

**Motivo:** Una aplicación de Planning Poker pierde su utilidad si la mesa requiere F5/recargar para ver los votos de los demás. Requerimos notificaciones push desde el backend a todos los clientes de una sala concurrentemente con latencia baja.

**Consecuencias:**
- Requiere correr ASGI (como Daphane o Uvicorn) en lugar del tradicional WSGI en producción.
- Añade Redis a la matriz de dependencias e infraestructura.

---

## ADR-003 — Autoridad en el Servidor (Server-Side Authority)

**Estado:** Aceptado

**Decisión:** El frontend carece totalmente de poder sobre las validaciones, el estado de la ronda, y los cálculos estadísticos.

**Motivo:** Al existir roles (Facilitador, Invitado) y reglas estrictas de privacidad antes del *reveal*, la arquitectura no puede confiar en el lado del cliente (Navegador) para ocultar información, porque es fácilmente auditable o manipulable.

**Consecuencias:**
- Todo evento generado por el usuario ("Votar") es solo una "intención" que el Servidor debe ejecutar.
- El servidor deberá enviar estados consolidados por WebSockets a los clientes.

---

## ADR-004 — URL Compartida con Identificador Impredecible

**Estado:** Aceptado

**Decisión:** Las URL para unirse como invitado se basarán en un identificador alfanumérico aleatorio (ej. `public_id`).

**Motivo:** Facilitar el acceso rápido al equipo sin cuentas, y prevenir enumeración y robo de privacidad si se usaran identificadores numéricos incrementales.

---

## ADR-005 — Capa de juego cosmética y autoritativa en el servidor

**Estado:** Aceptado

**Decisión:** Añadir una capa de interacción entre pares — lanzar objetos blandos a
otra persona de la mesa — que es puramente cosmética, efímera y desactivable por dos
interruptores independientes. El servidor decide cada lanzamiento; el navegador sólo
envía una intención y espera el broadcast.

**Motivo:** La sala funcionaba pero se sentía como un formulario. La espera entre el
primer voto y el último es tiempo muerto, y es justo donde un equipo que está en la
misma sala bromearía. Queremos recuperar ese momento sin convertirlo en presión.

Esto **revierte una decisión anterior de producto**: `docs/ROOM_VISUAL_DESIGN.md`
traducía «atacar» como un recordatorio amable, exclusivo del facilitador. El
recordatorio se conserva, pero deja de ser la única interacción posible entre
personas.

**Consecuencias:**

- Dos eventos nuevos en el protocolo: la acción `player.throw {target_id, item}` y el
  evento `player.hit {thrower_id, target_id, item}`. El payload se comprueba con
  igualdad exacta en los tests: es todo el contrato, y no cabe nada más.
- Tres campos nuevos: `PokerRoom.allow_playful_actions`,
  `Participant.last_throw_at` y `Participant.throws_this_round`.
- Los límites viven en `rooms/services.py`, no en el cliente: 2,5 s de espera por
  persona y un tope por ronda. El navegador no puede concederse un brazo más rápido.

**Reglas que hacen que esto siga siendo un juego.** Son parte de la decisión, no una
nota al pie:

1. **El voto sigue privado.** Ni `player.throw` ni `player.hit` transportan
   información de voto, y hay un test que lo verifica con igualdad exacta del payload.
2. **El objeto es idéntico haya votado el destinatario o no.** Las comprobaciones del
   servicio son deliberadamente ciegas a `current_vote`, así que un lanzamiento nunca
   puede leerse como una señal sobre la carta de alguien ni sobre su silencio.
3. **Nada acumula.** `throws_this_round` muere con la ronda. No hay marcador de quién
   recibió más impactos ni ranking de quién tardó más.
4. **Nada automático ni dirigido por estado.** Ningún objeto sale solo hacia quien no
   ha votado, y el aro de puntería aparece igual sobre todas las caras.
5. **El catálogo se queda blando.** Comida, papel y objetos de oficina absurdos.
   Ningún objeto que lea como arma o como daño.
6. **Doble consentimiento.** El facilitador apaga la capa para toda la sala;
   cada persona puede apagar los efectos en su propia pantalla. Y
   `prefers-reduced-motion` manda por encima de ambos.
7. **La reunión gana.** Nada tapa la mano de cartas ni el botón de revelar, nada
   bloquea la entrada, y los proyectiles y las manchas del paño tienen tope.

**Alternativa descartada:** dejar el «ataque» sólo como recordatorio del facilitador.
Es más seguro, pero mantiene la asimetría que hacía que la sala se sintiera como un
panel de administración: una persona con controles y el resto esperando.

---

## ADR-006 — Sistema de diseño de Nxtara y carcasa de aplicación en móvil

**Estado:** Aceptado

**Decisión:** Adoptar el sistema de diseño de Nxtara como lenguaje visual del producto, y
hacer que por debajo de 821px la interfaz se comporte como una aplicación móvil en lugar de
como una página web estrecha.

**Motivo.** Planning Pocket tenía un sistema visual propio —verde paño, acento terracota—
coherente consigo mismo pero ajeno al resto del software de la empresa. Mantener dos lenguajes
cuesta dos veces y no compra nada: el producto se presenta junto a los demás y debe reconocerse
como parte de lo mismo. En móvil, además, había un agujero real: a partir de 700px los enlaces
del encabezado se ocultaban por falta de sitio y no reaparecían en ningún otro lugar, así que
desde un teléfono no se podía crear una sala ni cerrar sesión.

**Cómo se implementa.** Las primitivas de Nxtara se declaran una sola vez con prefijo `--nx-*`
y se traducen a los nombres semánticos que ya consumían los componentes (`--surface`,
`--accent`, `--felt`, `--radius-*`…). Ningún componente lee una primitiva directamente. Esto es
lo que permitió cambiar la marca entera tocando el bloque de tokens y un puñado de reglas, en
lugar de reescribir la hoja: la geometría de la mesa, que está verificada al píxel por los tests
de navegador, no se tocó.

**Consecuencias:**

- El rosa `#ed117b` no pasa AA sobre blanco para texto normal (4,2:1). Se parte en dos tokens:
  `--brand` decora y nunca lleva texto; `--accent` es el interactivo y está rebajado hasta pasar.
  Quien cambie uno por el otro rompe el contraste sin verlo.
- **Una superficie que no cambia con el tema no puede llevar texto de un token que sí cambia.**
  Esto no se dedujo: se encontró midiendo. La cara de la carta es clara en los dos temas y
  `.participant-front.no-vote` usaba `--muted`, que en oscuro es blanco: al revelar, el guion de
  «no votó» quedaba en 1,08:1, invisible. Lo mismo con el rótulo sobre el panel de marca
  (`--brand-bright`, 4,1:1). Las tres superficies fijas —cara de carta, panel de marca y paño—
  derivan su tinta de sí mismas, nunca del tema. Ver `docs/PRODUCT.md`.
- El paño de la mesa es violeta en ambos temas. Los asientos siempre caen sobre él, así que la
  paleta de asientos tampoco cambia con el tema, igual que antes.
- Manrope e Inter se cargan desde Google Fonts, con la familia del sistema como respaldo. Es la
  primera dependencia de red del frontend; si no carga, el texto se dibuja con la pila de
  respaldo y nada se descoloca.
- El tema oscuro pasa a ser la lectura canónica de la marca. El claro se mantiene, y la
  preferencia del usuario sigue mandando sobre la del sistema.
- En móvil aparecen dos elementos anclados que antes no existían —la barra de pestañas y la
  baraja— y ninguno puede tapar lo que hay debajo. La altura de la baraja se **mide** y se
  publica en `--deck-dock-height`, en lugar de reservar un hueco fijo que sobraría o faltaría
  según la bandeja de objetos esté abierta o no.

**Alternativa descartada:** quedarnos con la paleta propia y sólo «acercarla» al rosa de Nxtara.
Habría dado un producto que no es ni una cosa ni la otra, y el coste de mantener dos lenguajes
se paga igual.

---

## ADR-007 — Moderación de la sala: dos barajas y expulsión con veto

**Estado:** Aceptado

**Decisión:** El facilitador gana dos poderes sobre la sala. Primero, la baraja por
defecto pasa a ser de ocho cartas (`0 1 2 3 5 8 13 ?`) y un interruptor la lleva a las
trece de siempre. Segundo, puede expulsar a un participante, y la expulsión **veta**:
esa persona no vuelve a entrar con el mismo enlace.

**Motivo.** Trece cartas en un teléfono se recorren de lado, y las cuatro últimas de
Fibonacci sirven para discutir una vez al trimestre. Y una sala que se comparte por un
enlace impredecible pero público necesita que quien la abre pueda cerrarle la puerta a
alguien, por el motivo que sea: un nombre que no corresponde, una pestaña zombi, una
persona que no debería estar.

**Cómo se implementa, y lo que no es obvio:**

- **Dos listas cerradas, no una baraja configurable.** Viven en `rooms/decks.py`, como
  las mascotas viven en `identity.py`. Una baraja escrita a mano obliga a validar
  longitud, duplicados y qué cuenta como numérico para el promedio, a cambio de una
  libertad que nadie pidió. `is_expanded()` se deriva de lo guardado en lugar de llevar
  un booleano aparte, para que no puedan contradecirse.
- **Al encoger, los votos huérfanos se retiran.** Un voto de una carta que ya no está
  en la mesa aparecería al revelar como un 55 que no se puede volver a elegir, y el
  promedio lo contaría: un número que nadie puede reproducir. El evento lleva a quién
  le pasó, para que lo vea en el momento y no al final.
- **La baraja no cambia bajo una ronda revelada**, igual que el recreo no se abre con
  las cartas sobre la mesa. Cambiarla ahí reescribe un resultado que se está discutiendo.
- **La expulsión no borra la fila: la fila *es* el veto.** `Participant.removed_at`
  marca la salida y el registro se queda, porque guarda el `guest_token` —o el usuario—
  con el que esa persona volvería a entrar. Borrarla dejaría que volviese con el mismo
  enlace diez segundos después, que es exactamente no haber expulsado a nadie.
- Por eso aparece `PokerRoom.active_participants`: **cualquier sitio que dibuje, cuente
  o promedie la mesa tiene que pasar por ahí**, y `_get_seated()` protege cada acción
  sobre un participante. Sin esa segunda guarda, el socket que el expulsado ya tenía
  abierto seguiría votando.
- El veto se comprueba en los dos sitios por los que se entra: la vista HTTP —el
  cliente recarga la página en cuanto se le cierra el socket— y `get_participant()` del
  consumer, porque reconectar es lo primero que hace el cliente al caerse.

**Límite conocido, y es real:** un invitado expulsado que vacíe las cookies del
navegador puede volver a entrar como alguien nuevo. La identidad de un invitado es su
`guest_token` y no hay nada más fuerte que vetar sin pedir una cuenta. Para un
participante autenticado el veto es contra el usuario y sí es firme. No lo tapamos con
IP: castigaría a toda una oficina detrás del mismo NAT.

**Alternativa descartada:** una expulsión blanda, que sólo saca de la mesa y deja
volver. Es mucho más simple —no hay nada que persistir— pero sirve para limpiar un
nombre mal escrito, no para apartar a alguien, que es lo que se pidió.

---

## ADR-008 — Endurecimiento tras la revisión de seguridad

**Estado:** Aceptado

**Decisión:** Cerrar los huecos que encontró una revisión completa del código. No es una
funcionalidad nueva: es la diferencia entre un modelo de autorización correcto sobre el
papel y uno que también lo es cuando alguien empuja.

**Los tres que importan, y por qué no se veían:**

1. **Sin límite en lo que escribe.** Las acciones decorativas tenían freno —lanzar espera
   2,5 s, moverse 110 ms— y votar no tenía ninguno. Medido contra el contenedor: 300
   `vote.cast` seguidos, cero errores, reparto completo. Cada uno es un `SELECT FOR
   UPDATE` sobre la sala más N frames. Y como la sala no tenía tope, N lo elegía el
   atacante. Ahora hay ventana deslizante por conexión y `MAX_PARTICIPANTS`.

2. **La sesión no alcanzaba a los sockets abiertos.** `AuthMiddlewareStack` resuelve
   `scope["user"]` una vez, al conectar, y ahí leían todas las comprobaciones de
   facilitador. Cerrar sesión no le quitaba el control de la sala a nadie hasta que
   cerrase la pestaña. `live_actor()` relee la sesión en cada acción de facilitador.

   Esto obligó a cambiar el banco de pruebas: los tests de WebSocket autenticaban
   poniendo `scope["user"]` a mano, que es algo que producción nunca hace. Ahora crean
   una sesión real. Un banco que se salta la sesión no prueba el camino que importa.

3. **Sin CSP.** Mil líneas de JavaScript en línea, manejadores `onclick` incrustados y un
   `innerHTML` alimentado con el nombre que escribe un invitado. Ese `innerHTML` se
   defendía borrando comillas dobles y **no llegaba a ser explotable** —verificado en
   navegador con cuatro payloads, cero ejecuciones— pero era una lista negra en un sink
   de HTML. Ahora se construye nodo a nodo, los `onclick` son listeners delegados, y la
   política con nonce impide que un script inyectado corra aunque entre.

**Lo demás, en una línea cada uno:**

- `player.move` era la única acción que no pasa por `rooms/services.py`, y por tanto la
  única sin `_require_active_room`: se podía pasear por una sala cerrada. Ahora el cierre
  cierra el recreo y avisa por el canal, de modo que cerrar una sala alcanza a quien ya
  está dentro en vez de ser sólo una fila en la base.
- Fuerza bruta: `accounts/throttling.py`, contando por usuario y no por IP, porque detrás
  de un proxy contar por IP es confiar en una cabecera falsificable o castigar a toda una
  oficina.
- Nadie podía saber quién era el facilitador: la insignia existía sólo en su propia barra.
  `is_facilitator` viaja ahora en el estado del participante.
- `PokerRoom.reset_voting()` era código muerto **y además saltaba la autorización**: quien
  lo llamara reiniciaba la ronda sin pasar por `_require_facilitator`. Borrado.
- `config/asgi.py` creaba el superusuario en tiempo de importación, con un `except
  Exception` mudo, duplicando lo que ya hacen el entrypoint y `build.sh`. Borrado.
- Una 404 devolvía `{"error": "Not found"}` en JSON. El producto entero entra por un
  enlace compartido, así que teclear mal el enlace es el error más probable que existe.
- `LANGUAGE_CODE` era `en-us` en un producto en español, y no había `LOGGING`: los 500
  iban a `mail_admins` sin `ADMINS`, o sea a ninguna parte. Así vivió el fallo de Redis.

**Un hallazgo de la revisión resultó ser falso**, y conviene dejarlo escrito para que nadie
lo "arregle": el bloque `MAILERS` de `settings.py` parece configuración muerta porque no
aparece en `django.conf.global_settings`. No lo es. `MAILERS` es la API de correo de
Django 6.1 y `EMAIL_BACKEND` está deprecado, retirado en 7.0; definir los dos a la vez es
un error de configuración. El código estaba bien.

**Concesión explícita:** `style-src` admite `'unsafe-inline'`. La mesa coloca cada asiento
escribiendo `style="--seat-angle: …"`, y un atributo de estilo no se puede firmar con
nonce. Quitarlo exigiría mover la geometría del anillo a clases, que es precisamente lo
que el ADR anterior evitó para no tocar una geometría verificada al píxel.
