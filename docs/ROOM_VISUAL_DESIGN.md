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
- Mascota y color se eligen en la pantalla de ingreso y se pueden cambiar en cualquier momento
  desde el panel «Personaje» de la barra superior, que es la única vía para los participantes
  autenticados: nunca ven la pantalla de ingreso. Sólo se puede cambiar el propio asiento. La cara
  se deriva.
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

El facilitador puede enviar un recordatorio amable, sólo a participantes conectados que aún no
votan, con un máximo de una vez cada 20 segundos por participante. La señal es una breve onda de
acento; no envía mensajes y no expone votos.

## Capa de juego

Cualquiera puede lanzar un objeto blando a la cara de otra persona de la mesa. Es decoración: no
cambia ningún voto, no bloquea nada y no persiste más allá de un contador que muere con la ronda.
Las reglas completas están en `docs/DECISIONS.md` ADR-005; lo relevante para el diseño visual:

- **La cara es el blanco.** Sólo el avatar es interactivo, nunca el asiento completo, para que el
  botón de recordatorio no acabe anidado dentro de otro botón. Es un `<button>` real: se alcanza con
  Tab, las flechas izquierda y derecha recorren la mesa, y el aro de puntería aparece igual en hover
  y en foco.
- **El aro aparece igual sobre todas las caras**, haya votado la persona o no.
- El objeto describe una parábola de cara a cara, deja una mancha en el paño que se desvanece en
  2,5 s, y provoca un encogimiento de 520 ms en el avatar más un salto de susto en la mascota.
- Hay tope de proyectiles simultáneos y de manchas en el paño, para que una mesa animada no se
  convierta en sopa.
- El proyectil tiene además un plazo límite: si el reloj de frames está frenado, el objeto aterriza
  igual en lugar de quedarse colgado sobre el paño.
- **Dos interruptores en la barra superior.** «Juego» es del facilitador y afecta a toda la sala;
  cuando está apagado la bandeja desaparece en lugar de quedarse gris invitando a clics que serán
  rechazados. «Efectos» es personal, se recuerda en el navegador y sólo afecta a esa pantalla.
- La mascota tiene un cuarto estado, asustada, que sólo existe aquí porque es aquí donde está el
  impacto que lo dispara.

## Modo recreo

Mientras la mesa espera el último voto, el facilitador puede abrir un recreo: las personas se
levantan de su asiento y caminan por la sala.

- **Es una capa sobre la reunión, nunca un reemplazo.** Los asientos siguen visibles debajo,
  atenuados al 34 %, así que nadie pierde de vista quién ha votado. La mano de cartas queda fuera de
  la capa y nunca se tapa: se puede votar caminando.
- Cuatro puntos de interés en las esquinas del paño: cafetera, dispensador, pizarra y ventana.
- Se mueve haciendo clic en el suelo o con las flechas.
- Estar en la cafetera es una **señal social**, no un estado que el servidor imponga: el avatar
  carga una taza y el estado del asiento pasa a decir `En pausa`, en texto como todos los demás
  estados. La persona sigue en la ronda y su voto sigue contando.
- Al acercarse a alguien aparece un saludo breve.
- **El recreo se cierra solo al revelar.** El servidor lo cierra en `reveal_round` y avisa antes de
  emitir el reveal, así que los avatares caminan de vuelta a su asiento mientras corre la cuenta
  atrás y la coreografía arranca desde una mesa sentada.
- En móvil no se ofrece: sin anillo elíptico no hay paño por el que caminar.

Las posiciones son **efímeras**: coordenadas normalizadas de 0 a 1 que el servidor reenvía sin
guardar nada. Un cliente que se retrasa pierde la posición intermedia en lugar de acumular cola, y
el servidor descarta en silencio lo que llegue más rápido que un movimiento cada 110 ms.

## Sonido

Cinco tonos sintetizados con WebAudio en el momento: apoyar carta, giro, lanzamiento, impacto y un
acorde de consenso. No se descarga ningún archivo, así que no cuesta ni una petición ni un byte.

- **Apagado por defecto**, con un único interruptor que se recuerda en el navegador.
- El `AudioContext` se crea sólo después de un clic real, porque los navegadores rechazan crearlo
  antes.
- Si el navegador no da audio, la sala sigue en silencio sin romperse.
- El giro suena una vez por carta durante el reveal escalonado, así que la mesa se oye como una
  baraja pasando.

## Estado de una sola persona

Una persona en la mesa es un estado normal, no uno roto. El paño muestra su mascota y una invitación
a compartir el enlace, en lugar de un óvalo desierto con un contador de uno.

## Presupuesto de rendimiento

Las catorce animaciones de la hoja de estilos tocan únicamente `transform` y `opacity`. Nada anima
propiedades que disparen layout, y eso incluye los caminantes del recreo: se mueven con `transform`
y no con `left`/`top`, leyendo el rectángulo de la capa una vez por pasada y no una vez por
caminante. `will-change` se usa en un solo sitio, justamente ahí.

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

No hay ninguno. Había una exploración estática en `prototype/index.html` que dejó de reflejar la
mesa, y un prototipo obsoleto engaña más de lo que ayuda. La sala real es ahora la referencia, y su
geometría y sus estados se verifican midiendo el DOM. El archivo sigue en el historial de git.
