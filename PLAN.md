# Trabajo Pendiente

## Fase 3 — Interacción entre jugadores

- Acción `player.throw {target_id, item}` y evento `player.hit`, validados en `rooms/services.py`
  con la misma disciplina que `cast_vote`.
- Límite autoritativo en el servidor: un lanzamiento cada 2,5 s por persona y un tope por ronda,
  siguiendo el patrón ya existente de `last_reminded_at`.
- Seis objetos con su arco, giro y calcomanía: tomate, bola de papel, café, almohada, sello
  «APROBADO», zapatilla. Tope de proyectiles simultáneos y de calcomanías en el paño.
- Cuarto estado de la mascota, «asustada»: salta hacia atrás y vuelve. Se implementa aquí, con el
  impacto que lo dispara, y no antes.
- Cualquiera puede lanzar a cualquiera; el facilitador deja de ser especial. Apuntar es hacer clic
  en un asiento, con aro de puntería al pasar por encima.
- Camino de teclado: flechas para seleccionar asiento, Enter para lanzar.
- Añadir `PokerRoom.allow_playful_actions` (interruptor del facilitador para toda la sala) y una
  preferencia personal de «reducir efectos» recordada en el navegador.
- Reglas que no se negocian, porque sin ellas la capa deja de ser un juego:
  - El objeto es idéntico haya votado el destinatario o no.
  - Nada de lanzamientos automáticos ni de puntería que aparezca sólo sobre quienes faltan.
  - Nada de marcadores acumulativos («más lento», «más golpeado»): los contadores mueren con la
    ronda.
  - Nada de objetos que lean como violencia.
- Tests: límite de tasa, sala con juego apagado, y que el payload de `player.hit` no transporte
  datos de voto.
- Registrar ADR-005: capa de juego cosmética y autoritativa en el servidor.
- Actualizar la sección de recordatorio en `docs/ROOM_VISUAL_DESIGN.md`.

## Fase 4 — Modo recreo

- Disponible sólo en fase de votación y sólo si el facilitador lo habilita.
- La mesa se aleja y aparece el suelo con cuatro puntos de interés: cafetera, dispensador,
  pizarra, ventana.
- `player.move {x,y}` a 8 Hz, efímero: nunca se persiste y se descarta al revelar. Bajo presión se
  descarta la posición intermedia, no se encola.
- Proximidad: gesto corto al acercarse a alguien; en la cafetera el avatar carga una taza y queda
  marcado «en pausa» como señal social, no como estado que el servidor imponga.
- Al revelar, todos caminan de vuelta a su asiento en 700 ms y luego arranca la coreografía de
  reveal existente.
- Votar sigue siendo posible mientras se camina: la mano de cartas permanece anclada.
- Requiere Redis en producción (ADR-002). Es la única parte del plan con coste de infraestructura.

## Fase 5 — Sonido y remate

- Cinco tonos sintetizados con WebAudio (apoyar carta, giro, lanzamiento, impacto, acorde de
  consenso). Sin descargas, apagado por defecto, un único interruptor recordado en el navegador.
- Estado vacío digno: con una sola persona, la mesa muestra su mascota y un crupier en reposo.
- Presupuesto de rendimiento: sólo `transform` y `opacity`, `will-change` con cuentagotas.
- Reemplazar `prototype/index.html` por un prototipo que refleje la mesa y la capa de juego
  actuales.

## Deuda de acabado detectada en la auditoría

- La barra lateral de historias fuerza el alto del layout con `min-height: 678px` y pesa más que la
  mesa. Hacerla plegable y devolver el protagonismo al paño.
- Los participantes autenticados no pueden elegir mascota ni color: reciben una identidad derivada.
  Sólo los invitados pasan por el selector, porque son los únicos con una pantalla de ingreso.
