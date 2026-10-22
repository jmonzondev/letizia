#!/bin/bash
# copia generada por capa_proyecto.sh desde ~/.claude: edita el original, no esta copia
# UserPromptSubmit: si algo está sonando en el Mac (afplay o say), se calla en cuanto Jose envía un mensaje.
# Nunca imprime nada: en este evento, lo que sale por stdout entra en el contexto de Claude.
pkill -x afplay >/dev/null 2>&1
pkill -x say >/dev/null 2>&1
exit 0
