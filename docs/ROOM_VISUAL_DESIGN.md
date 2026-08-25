# Mesa de cartas — especificación visual

## Intención

La sala debe sentirse como una mesa de Planning Poker compartida, no como un panel de
administración. La historia y el estado de la ronda ocupan el centro; las personas se representan
por cartas alrededor de la mesa. La baraja del usuario permanece siempre a mano.

## Jerarquía

1. Historia activa y fase de la ronda.
2. Mesa y participantes.
3. Baraja personal.
4. Acciones de facilitación y cola de historias.

## Cartas de participante

- El reverso azul oscuro indica que la persona ya votó, sin revelar su valor.
- Una carta clara con una pequeña etiqueta `Pensando` indica que está conectada y aún no vota.
- Una carta apagada indica que la persona está ausente; no se usa como señal de presión.
- Al revelar, cada carta gira para mostrar el voto. Las personas sin voto conservan una cara
  neutra `—`.
- El nombre aparece siempre bajo la carta. La carta del usuario tiene un anillo de acento y la
  etiqueta `Tú`.

## Recordatorio a participantes pendientes

“Atacar” se traduce como un recordatorio amable del facilitador. Sólo el facilitador lo puede
activar, únicamente para participantes conectados que aún no votan, con un máximo de una vez cada
20 segundos por participante. La señal es una breve onda de acento y el texto “Aún decidimos”; no
envía mensajes, no expone votos y respeta `prefers-reduced-motion`.

## Responsive y accesibilidad

- Escritorio: los participantes se distribuyen alrededor de una mesa ovalada.
- Tableta: la mesa conserva la composición, con una cola de historias plegable.
- Móvil: las cartas pasan a una franja horizontal que conserva nombre, estado y orden; la historia
  y baraja se mantienen visibles sin depender de hover.
- Todos los estados se expresan con texto además de color. Las animaciones se desactivan con
  `prefers-reduced-motion`; los botones y cartas son operables con teclado.

## Prototipo

`prototype/index.html` demuestra votación, reveal, reinicio, recordatorio y adaptación móvil con
datos ficticios. No contiene lógica de negocio ni se conecta a WebSocket.
