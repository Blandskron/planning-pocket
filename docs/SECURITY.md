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
HTML con datos de participantes o issues. Esto dejó de ser una promesa y pasó a ser cierto en la
revisión de seguridad: quedaba un `innerHTML` en `createParticipantCard` que metía el nombre del
invitado en un atributo con una única defensa, borrar comillas dobles. No llegó a ser explotable
—dentro de un valor entrecomillado `<` y `>` son inertes, y se verificó en navegador con cuatro
payloads: cero ejecuciones— pero era una lista negra en un sink de HTML, y ahora se construye
nodo a nodo con `setAttribute`.

## 7. Content-Security-Policy

- **Riesgo:** La sala ejecuta cerca de mil líneas de JavaScript en línea. Cualquier inyección de
  HTML que llegue al DOM se convierte en ejecución de código.
- **Mitigación:** `config/middleware.py` emite una CSP con nonce por petición. `script-src` sólo
  admite el propio origen y el nonce de esa respuesta, así que un script inyectado no corre
  aunque consiga entrar en el documento. `style-src` sí admite `'unsafe-inline'`: la mesa coloca
  los asientos con atributos `style`, que no se pueden firmar. La protección que importa está en
  `script-src`.
- `DJANGO_CSP_REPORT_ONLY=true` cambia a modo informe para estrenar cambios sin bloquear.

## 8. Agotamiento de recursos

- **Riesgo:** Las acciones decorativas tenían freno —lanzar espera 2,5 s, moverse 110 ms— y las
  que escriben en la base no tenían ninguno. Medido: 300 `vote.cast` seguidos, cero errores,
  reparto completo a toda la mesa. Con salas sin tope, el coste crece con el cuadrado del número
  de participantes.
- **Mitigación:** ventana deslizante por conexión en el consumer para toda acción que escriba
  (`WRITE_MAX_IN_WINDOW` en `WRITE_WINDOW_SECONDS`), y `MAX_PARTICIPANTS` por sala. El cliente
  deshace su selección optimista cuando el servidor rechaza, para que la pantalla no diga algo
  distinto de la mesa.

## 9. Vigencia de la sesión en sockets abiertos

- **Riesgo:** `AuthMiddlewareStack` resuelve `scope["user"]` una sola vez, al conectar. Si la
  autorización se queda ahí, cerrar sesión no le quita a nadie el control de la sala hasta que
  cierre la pestaña: sigue pudiendo revelar, reiniciar, cambiar la baraja y expulsar.
- **Mitigación:** `PokerConsumer.live_actor()` relee la sesión del almacén en cada acción de
  facilitador y delega en `django.contrib.auth.get_user`, que además comprueba el hash de sesión,
  así que un cambio de contraseña también corta el socket abierto.

## 10. Fuerza bruta sobre el acceso

- **Riesgo:** Ni el login ni el registro tenían freno.
- **Mitigación:** `accounts/throttling.py` cuenta intentos fallidos **por nombre de usuario**, no
  por IP. La aplicación corre detrás de un proxy, así que contar por IP obliga a confiar en una
  cabecera que cualquiera puede escribir, o a meter a toda la empresa en el mismo cubo. El coste
  conocido es que se puede bloquear una cuenta ajena a propósito: por eso la ventana es corta, no
  se renueva con cada intento, y entrar bien borra el contador.

## 11. Suplantación del facilitador

- **Riesgo:** Un invitado puede ponerse el nombre del facilitador. La insignia existía sólo en la
  barra del propio facilitador, así que nadie más en la mesa podía distinguirlos. Desde que el
  facilitador puede expulsar, dejó de ser cosmético.
- **Mitigación:** `is_facilitator` viaja en el estado del participante —no es secreto, sus
  controles se ven— y la mesa dibuja la marca en el asiento.

## 7. Configuración de producción

- `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS` son obligatorios con `DJANGO_DEBUG=False`; no hay
  valores de respaldo inseguros.
- `DATABASE_URL` admite URLs `postgres://`/`postgresql://` y configura PostgreSQL; sin ella se usa
  SQLite sólo para desarrollo local.
- `DJANGO_CSRF_TRUSTED_ORIGINS` debe contener los orígenes HTTPS públicos separados por comas.
- HSTS, cookies seguras, redirección HTTPS y el backend SMTP se activan en producción. Docker no
  incorpora secretos: deben entregarse como variables de entorno en tiempo de ejecución.
