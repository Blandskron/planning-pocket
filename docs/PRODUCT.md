# Planning Pocket - Producto y UX

## 1. Visión del Producto
Alternativa gratuita, moderna, profesional, rápida y sencilla de usar a Planning Poker Online.
Flujo central: Crear sala → compartir enlace → escribir nombre → votar.

## 2. Personas

### Persona 1: Facilitador
- **Perfil**: Scrum Master, Product Owner o Tech Lead.
- **Necesidades**: Crear salas rápidamente sin fricción. Compartir el link al instante por chat o videollamada. Controlar el flujo de la sesión (cuándo se revela, cuándo se reinicia). Mantener el enfoque del equipo en la estimación.
- **Permisos**: Crear sala, invitar, iniciar votación, revelar, reiniciar, cerrar sala, gestionar tareas (issues), alternar entre la baraja corta y la completa, y **expulsar a un participante** de la sala (ver ADR-007).

### Persona 2: Participante Invitado
- **Perfil**: Desarrollador, QA o Diseñador de un equipo ágil.
- **Necesidades**: Entrar a la sala con un solo click y su nombre, sin crear cuenta. Entender inmediatamente cómo votar. Ver quién más está en la sala. Conocer los resultados una vez revelados.
- **Permisos**: Entrar, votar, cambiar voto (antes del reveal), salir. NO puede revelar, gestionar la sala, cambiar la baraja ni expulsar a nadie. Puede ser expulsado por el facilitador.

## 3. Flujos Principales

### Flujo: Crear Sala (Facilitador)
1. Usuario abre la Landing Page.
2. Inicia sesión (o crea cuenta si no tiene).
3. Accede al Dashboard (lista de salas pasadas/activas).
4. Hace click en "Nueva Planning Poker".
5. Entra a la nueva sala (ej: `/p/7Xs92Klm`).
6. Copia el enlace y lo comparte con su equipo.

### Flujo: Entrar como Invitado (Participante)
1. Abre el enlace compartido.
2. Ve una pantalla de "Ingreso de nombre" (ej. placeholder: "Tu nombre...").
3. Escribe su nombre y presiona "Entrar".
4. Accede a la sala como participante activo.

### Flujo: Votación
1. El facilitador lee/añade la historia a estimar.
2. Cada participante selecciona una carta de la baraja (ej. 1, 2, 3, 5, 8...).
3. Mientras se vota, todos ven quiénes han votado (estado: ✅), pero NO el valor.
4. Cuando el equipo termina de votar, el facilitador presiona "Reveal".
5. Todos ven instantáneamente los votos, el promedio (si aplica), y si hay consenso.
6. Discuten si es necesario.
7. Facilitador presiona "Siguiente ronda" o "Reiniciar" para continuar.

## 4. Arquitectura de Información e Interfaz (Sala)

### Layout Principal
- **Header**: Nombre de la sala, enlace rápido para copiar, estado de conexión.
- **Sidebar (o panel superior/izquierdo)**: Lista de Issues/Tareas.
- **Centro (Mesa)**: Área principal con la historia actual, estado ("Votando...", "Resultados"), y avatares/nombres de participantes con sus estados de voto (pensando / votó / [Valor]).
- **Bottom (Baraja)**: Cartas grandes y accesibles. Por defecto ocho —`0, 1, 2, 3, 5, 8, 13, ?`—; el facilitador las amplía a `0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ?, ☕` con el interruptor «Baraja larga». Trece cartas en un teléfono se recorren de lado.
- **Controles de Facilitador**: Botones flotantes o en bloque central: "Reveal", "Reiniciar", "Siguiente".

## 5. Design System

Planning Pocket usa el **sistema de diseño de Nxtara**. No es una paleta inspirada en él: son
sus mismas primitivas de marca, sus mismos radios y su misma tipografía, declaradas una vez en
`static/css/style.css` bajo el prefijo `--nx-*` y traducidas desde ahí a los nombres semánticos
que consumen los componentes (`--surface`, `--accent`, `--felt`…). Cambiar de tema es cambiar esa
traducción, no repintar componentes.

### Primitivas de marca

| Token | Valor | Papel |
| --- | --- | --- |
| `--nx-rosa` | `#ed117b` | La acción. Es el único color con el que se pulsa algo. |
| `--nx-rosa-clara` | `#ff4da3` | Apoyo: brillos, bordes de foco, acentos sobre fondo oscuro. |
| `--nx-campo-azul-inicio` | `#202b70` | Inicio del campo de página. |
| `--nx-campo-azul-fin` | `#302665` | Giro del campo hacia el violeta. |
| `--nx-campo-violeta` | `#3b246f` | El paño de la mesa. |
| `--nx-campo-ciruela` | `#64104f` | Cierre del campo, abajo del todo. |
| `--nx-verde` / `--nx-ambar` / `--nx-rojo` | `#34d399` / `#fbbf24` / `#fb7185` | Semántica: votó, pendiente, error. |

### Temas

Nxtara es una marca oscura, así que **el tema oscuro es la lectura canónica**: campo azul →
violeta → ciruela, superficies translúcidas sobre ese campo, texto blanco y rosa como única
acción. El tema claro es su traducción a papel: fondo lavanda muy claro, tinta índigo, la misma
acción rosa rebajada hasta pasar AA sobre blanco.

El rosa de marca (`--brand`) y el rosa interactivo (`--accent`) son tokens distintos a propósito.
`#ed117b` sobre blanco da 4,2:1 y no pasa AA para texto normal, así que decora —resplandores,
bordes, reversos de carta— y nunca lleva texto encima. `--accent` sí, y por eso está rebajado en
claro (`#c7005f`) y aclarado en oscuro (`#ff80bd`): sobre las superficies translúcidas del tema
oscuro un rosa más saturado se queda por debajo de 4,5:1.

El paño de la mesa es violeta en los dos temas: los asientos siempre caen sobre él, así que su
paleta no tiene que cambiar.

### La regla que más fácil se rompe

**Una superficie que no cambia con el tema no puede llevar texto de un token que sí cambia.**

Hay tres de esas superficies: la **cara de la carta** (`--card-face`, clara siempre, porque una
carta es un objeto claro), el **panel de marca** del login y el registro (azul Nxtara siempre) y
el **paño**. El texto que cae encima se deriva de la propia superficie
(`color-mix(in srgb, var(--card-ink) 62%, var(--card-face))`) o es un literal relativo a ella
(`#ff9ac9` para el rótulo sobre el panel). Usar `--muted` o `--text-soft` ahí compila, pasa los
tests y desaparece en uno de los dos temas.

Medido sobre el DOM renderizado, componiendo el fondo real de cada texto: **0 fallos AA** en las
seis pantallas, con mínimos de 4,82:1 en oscuro y 4,66:1 en claro.

### Tipografía

- Títulos: **Manrope** (600/700/800), con `letter-spacing` negativo.
- Texto y números de carta: **Inter** (400/500/600/700).
- Ambas con familia de respaldo del sistema, por si la fuente no carga.

### Forma y movimiento

- Radios: control `14px`, tarjeta `22px`, panel `28px`, píldora `999px`. Los botones son píldoras;
  no hay rectángulos de esquina pequeña en acciones.
- Curva de animación: `cubic-bezier(.22, .61, .36, 1)`, a `.18s` (rápida) o `.35s` (media).
- Sombras de tarjeta con reflejo interior arriba (`inset 0 1px 0 rgba(255,255,255,.07)`), que es
  lo que separa un panel translúcido del campo que tiene detrás.

### Carcasa móvil

Por debajo de 821px la interfaz deja de comportarse como una página y pasa a comportarse como una
aplicación. Ver `docs/ROOM_VISUAL_DESIGN.md` para el detalle de la sala; en resumen:

- Barra superior fija y compacta con la identidad y el tema, respetando `env(safe-area-inset-top)`.
- **Barra de pestañas inferior** con los destinos de la app. Antes los enlaces del encabezado
  simplemente desaparecían en pantalla pequeña y no reaparecían en ningún sitio: el usuario de
  teléfono se quedaba sin crear sala ni cerrar sesión.
- En la sala, la baraja se ancla al borde inferior como la mano de cartas de un juego, y la barra
  de pestañas se retira para no competir por ese borde.
- `100dvh` en lugar de `100vh`, y `env(safe-area-inset-*)` en todo lo anclado.
