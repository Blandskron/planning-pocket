# Trabajo Pendiente

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
- Los mensajes de `RoomActionError` están en inglés y se muestran tal cual en un toast, dentro de
  una interfaz en español. Traducirlos y ajustar los `match` de los tests.
