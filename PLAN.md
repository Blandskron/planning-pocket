# Trabajo Pendiente

## Cobertura del consumer

`rooms/consumers.py` está al **67 %**, muy por debajo del resto (`services.py` al 96 %). El
umbral general de CI es 80 % y la suite está en 80,48 %, así que este archivo es lo que
sostiene el margen contra el suelo.

Lo que no está cubierto, en orden de importancia:

1. **Caminos de error del despacho.** Payload inválido, `event_type` desconocido, y una acción
   de facilitador enviada por alguien que no lo es. Debe responder un `error` estructurado
   sólo al socket que lo pidió, y no tocar a nadie más de la sala.
2. **Ciclo de conexión con varias pestañas.** `participant.joined` se emite en la primera
   pestaña y `participant.left` en la última que se cierra. `connection_count` es el contador
   que lo decide y sus bordes no tienen test.
3. **`player.moved`.** El descarte silencioso por debajo de los 110 ms y el rechazo cuando el
   recreo está cerrado.

No hace falta perseguir un número. Basta con que estos tres caminos existan como test; el
porcentaje sube solo y deja de ser el archivo que aguanta el umbral.
