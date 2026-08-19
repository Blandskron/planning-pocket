# Planning Pocket - Producto y UX

## 1. Visión del Producto
Alternativa gratuita, moderna, profesional, rápida y sencilla de usar a Planning Poker Online.
Flujo central: Crear sala → compartir enlace → escribir nombre → votar.

## 2. Personas

### Persona 1: Facilitador
- **Perfil**: Scrum Master, Product Owner o Tech Lead.
- **Necesidades**: Crear salas rápidamente sin fricción. Compartir el link al instante por chat o videollamada. Controlar el flujo de la sesión (cuándo se revela, cuándo se reinicia). Mantener el enfoque del equipo en la estimación.
- **Permisos**: Crear sala, invitar, iniciar votación, revelar, reiniciar, cerrar sala, gestionar tareas (issues).

### Persona 2: Participante Invitado
- **Perfil**: Desarrollador, QA o Diseñador de un equipo ágil.
- **Necesidades**: Entrar a la sala con un solo click y su nombre, sin crear cuenta. Entender inmediatamente cómo votar. Ver quién más está en la sala. Conocer los resultados una vez revelados.
- **Permisos**: Entrar, votar, cambiar voto (antes del reveal), salir. NO puede revelar ni gestionar la sala.

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
- **Bottom (Baraja)**: Cartas grandes y accesibles (Fibonacci modificado: 0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ?, ☕).
- **Controles de Facilitador**: Botones flotantes o en bloque central: "Reveal", "Reiniciar", "Siguiente".

## 5. Design System Inicial

### Colores
- Background: `#f9fafb` (Light)
- Surface: `#ffffff` (Cards, modales)
- Primary: `#2563eb` (Acciones principales, estados activos)
- Text: `#1f2937` (Base), `#4b5563` (Secundario)
- Success (Votó): `#10b981`
- Borders/Lines: `#e5e7eb`

### Tipografía
- Inter o similar (sans-serif moderna y limpia).

### Variables CSS Base
```css
:root {
  --color-bg: #f9fafb;
  --color-surface: #ffffff;
  --color-primary: #2563eb;
  --color-primary-hover: #1d4ed8;
  --color-text: #1f2937;
  --color-text-muted: #6b7280;
  --color-border: #e5e7eb;
  --color-success: #10b981;
  
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 1rem;
  --space-4: 1.5rem;
  --space-5: 2rem;
  
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 1rem;
}
```
