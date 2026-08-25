# Seguridad en Planning Pocket

Dado el enfoque colaborativo de la herramienta, se han identificado las siguientes consideraciones de seguridad.

## 1. Autorización (IDOR y Permisos)
- **Riesgo:** Un participante regular o invitado podría intentar ejecutar acciones reservadas para el Facilitador (ej. iniciar votación, revelar, expulsar participante).
- **Mitigación:** Toda acción crítica será interceptada y validada en el backend (Service Layer/Channels). Ocultar botones en la UI es secundario; la validación real exige verificar que el `User` o `Participant` autenticado es el propietario (owner) de la `PokerRoom`.

## 2. Privacidad de los Votos
- **Riesgo:** Durante el estado `VOTING`, clientes no autorizados podrían inspeccionar el tráfico de red o la consola y descubrir qué están votando sus compañeros antes del reveal.
- **Mitigación:** Mientras `state == VOTING`, la API o WebSocket enviará exclusivamente el estado de interacción (`has_voted: true`). El valor exacto del voto NO se leerá de la DB ni se inyectará en el payload hasta que el estado cambie a `REVEALED`.

## 3. Identidad de Invitados
- **Riesgo:** Manipulación del ID del invitado vía JavaScript para suplantar a otro votante.
- **Mitigación:** La identidad del invitado persistirá en el servidor (a través de la sesión de Django firmada en cookie). El frontend no definirá su propio `participant_id`.

## 4. Seguridad de WebSockets
- **Riesgo:** Inyección de mensajes, spam de reconexiones o escucha de salas ajenas.
- **Mitigación:**
  - Validación cruzada entre la conexión WebSocket y la sesión HTTP (`AuthMiddlewareStack`).
  - Validación del origen de la conexión (`AllowedHostsOriginValidator`).
  - Verificación estricta de pertenencia (un participante solo se suscribe al grupo Channel de su propia sala).
  - Rate Limiting básico contra payloads abusivos si es necesario.

La aplicación ASGI aplica `AllowedHostsOriginValidator`. Los clientes con un origen no incluido en
`DJANGO_ALLOWED_HOSTS` son rechazados antes de establecer la conexión.

## 5. Prevención de Enumeración
- **Riesgo:** Un atacante intenta barrer identificadores enteros secuenciales (`/p/1`, `/p/2`) para encontrar salas privadas.
- **Mitigación:** Las salas utilizarán un `public_id` seguro, largo e impredecible (ej. NanoID o UUID simplificado) para la URL.

## 6. Integridad y Entrada de Usuarios
- **Riesgo:** Cross-Site Scripting (XSS) a través de los nombres de los invitados o descripciones de historias.
- **Mitigación:** 
  - Django previene nativamente XSS en sus templates escapando el contenido.
  - Se aplicarán validaciones de longitud máxima y saneamiento básico de texto libre.

Los eventos WebSocket se insertan en el DOM mediante nodos y `textContent`, nunca interpolando
HTML con datos de participantes o issues.

## 7. Configuración de producción

- `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS` son obligatorios con `DJANGO_DEBUG=False`; no hay
  valores de respaldo inseguros.
- `DATABASE_URL` admite URLs `postgres://`/`postgresql://` y configura PostgreSQL; sin ella se usa
  SQLite sólo para desarrollo local.
- `DJANGO_CSRF_TRUSTED_ORIGINS` debe contener los orígenes HTTPS públicos separados por comas.
- HSTS, cookies seguras, redirección HTTPS y el backend SMTP se activan en producción. Docker no
  incorpora secretos: deben entregarse como variables de entorno en tiempo de ejecución.
