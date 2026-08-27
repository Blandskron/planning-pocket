# Mesa de cartas — especificación visual

## Intención

La sala debe sentirse como una mesa de Planning Poker compartida, no como un panel de
administración. La mesa es un **escenario**: el paño informa sobre la ronda, las personas se
sientan en un anillo alrededor y la baraja del usuario permanece siempre a mano como una mano de
cartas.

## Jerarquía

1. Historia activa y fase de la ronda.
2. Mesa, marcas del paño y participantes.
3. Resultado de la ronda revelada.
4. Mano de cartas personal.
5. Acciones de facilitación y cola de historias.

## Capas del escenario

El orden de apilamiento se declara una vez en tokens (`--z-felt`, `--z-marks`, `--z-decal`,
`--z-pets`, `--z-seats`, `--z-fly`, `--z-stage-ui`). Cualquier elemento nuevo sobre la mesa toma
su capa de esa lista en lugar de inventar un `z-index`.

## Asientos

Los asientos no tienen posiciones fijas. El cliente escribe `--seat-angle` y `--seat-index` en cada
asiento, y el CSS los coloca sobre una elipse con `cos()`/`sin()`.

Dos detalles importan y no son obvios:

- El reparto es por **longitud de arco**, no por ángulo igual. En una elipse el ángulo igual apiña
  los asientos en los extremos del eje menor y empiezan a solaparse alrededor de nueve personas.
- Los radios se derivan del espacio que **el asiento más grande** deja libre, no de un porcentaje
  fijo, y la altura del escenario crece por tramos (390 → 430 → 470 → 500 px) según la cantidad.
  Verificado sin solapes ni desbordes de 1 a 18 participantes.

Nada que cambie de tamaño durante la ronda puede estar en el flujo del asiento, o el anillo se
redimensiona a mitad de partida: por eso el botón de recordatorio es una capa absoluta.

El orden del anillo es el del servidor (`joined_at`, luego `id`), así que los vecinos son los mismos
para todo el mundo. El anillo se rota localmente para que cada persona vea su propio asiento abajo
al centro; la rotación es sólo un cambio de punto de vista, no de orden.

## Identidad en el asiento

Cada persona se dibuja con tres rasgos cosméticos: una **cara**, una **mascota** y un **color** de
la paleta de asientos (`--seat-hue-0` … `--seat-hue-6`, la misma en ambos temas porque los asientos
siempre están sobre el paño).

- Las opciones válidas viven en tuplas cerradas en `rooms/identity.py`; el formulario de ingreso
  valida contra ellas y nada más entra.
- Mascota y color se eligen en la pantalla de ingreso. La cara se deriva.
- Lo que no se elige se **deriva** de un hash estable del `guest_token` (`derive_identity`), así que
  los participantes creados antes de que estos campos existieran tienen un asiento reconocible sin
  migración de datos, y el mismo entre reconexiones.
- La identidad **no es secreta**: viaja en cada estado de participante, también con la votación
  abierta, porque es necesaria para dibujar el anillo. No dice nada sobre el voto.

## Mascotas

La mascota refleja el estado de su dueño con lenguaje corporal en lugar de con otra etiqueta:

- Sin votar: se adormila, con el ciclo más lento y una `z` flotando.
- Ya votó: da un pequeño salto y vuelve a su sitio.
- Ausente: se queda quieta y desaturada.

Las mascotas y las caras son símbolos SVG en `templates/rooms/_table_sprite.html`, referenciados con
`<use>`. Se definen una vez por página, así un asiento creado por WebSocket se dibuja igual que uno
renderizado por Django. Son decorativas: `aria-hidden` en el punto de uso, y el estado siempre está
además como texto.

## Cartas de participante

- El reverso terracota indica que la persona ya votó, sin revelar su valor. Al aparecer, la carta
  se apoya sobre la mesa con una animación breve.
- Una carta clara con la etiqueta `Pensando` indica que está conectada y aún no vota; los puntos
  suspensivos laten con suavidad.
- Una carta apagada indica que la persona está ausente; no respira y no se usa como señal de
  presión.
- Las cartas presentes respiran (±2,5 px, ciclos desfasados por `--seat-index`). Es lo que hace que
  la mesa parezca habitada.
- El nombre aparece siempre bajo la carta. La carta del usuario tiene un anillo de acento y la
  etiqueta `Tú`.

## Marcas del paño

El centro de la mesa informa en lugar de decorar:

- El montón de cartas repartidas crece con cada voto emitido.
- El contador `N de M han votado` es texto real en una región `aria-live="polite"`.
- Durante el reveal, una cuenta atrás ocupa el centro.

## Mano de cartas

La baraja se presenta como un abanico: las cartas se superponen y cada una recibe una rotación
derivada de `--card-index` y `--card-total`. El hover y la selección elevan la carta mediante
`--card-lift`, nunca sobrescribiendo el `transform` que sostiene el abanico.

Al votar, una carta fantasma viaja desde la mano hasta el asiento propio siguiendo un arco. El
gesto comunica «puse mi carta sobre la mesa»; el voto real lo decide el servidor.

## Coreografía del reveal

1. Cuenta atrás de tres tiempos sobre el paño, para que el último voto todavía quepa.
2. Las cartas giran una tras otra alrededor del anillo, con 70 ms de retardo por asiento.
3. Aterriza el panel de resultado.
4. Si hay unanimidad, el paño recibe un pulso dorado de 1,9 s.

Con `prefers-reduced-motion` la cuenta atrás y el escalonado se omiten: el resultado aparece de
inmediato.

## Resultado de la ronda

El resultado es el momento de mayor carga de la sesión y ocupa un panel, no una etiqueta: promedio,
rango, número de votos, veredicto de consenso y la distribución por valor. Sin consenso, las barras
de los extremos del rango se marcan en acento para que el equipo vea *dónde* se dividió.

El promedio se redondea en el servidor (`calculate_results`), porque el valor se renderiza tal cual.

## Recordatorio a participantes pendientes

Hoy «atacar» se traduce como un recordatorio amable del facilitador. Sólo el facilitador lo puede
activar, únicamente para participantes conectados que aún no votan, con un máximo de una vez cada
20 segundos por participante. La señal es una breve onda de acento; no envía mensajes, no expone
votos y respeta `prefers-reduced-motion`.

La capa de interacción entre pares (proyectiles, reacción de susto de la mascota, modo recreo) está
descrita como trabajo pendiente en `PLAN.md`, con sus reglas de consentimiento y privacidad.

## Responsive y accesibilidad

- Escritorio y tableta: los participantes se distribuyen sobre el anillo elíptico.
- Móvil: el anillo se desactiva y los asientos pasan a una franja horizontal desplazable que
  conserva nombre, estado y orden; las marcas del paño se convierten en una fila de texto sobre la
  franja. La historia y la mano se mantienen visibles sin depender de hover.
- Todos los estados se expresan con texto además de color. Las animaciones se desactivan con
  `prefers-reduced-motion`; los botones y cartas son operables con teclado.
- Los adornos del paño (óvalo, resplandor, montón, cuenta atrás) son `aria-hidden`; el contador de
  votos no lo es.

## Prototipo

`prototype/index.html` es una exploración estática anterior con datos ficticios. No refleja la
composición actual de la mesa ni contiene lógica de negocio.
