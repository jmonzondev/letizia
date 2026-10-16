<?php
// Formulario de contacto de /contacto/ (SPEC-LET-01).
//
// Recibe el envío del formulario, lo valida en el servidor y entrega el mensaje, una sola vez y como texto, en el correo
// de la clienta (CORREO_CONTACTO) hablando SMTP. Contesta con la propia página /contacto/ más el resultado, con o sin
// JavaScript. No guarda nada: ni ficheros, ni base de datos, ni cookies, ni sesión.
//
// Configuración, solo por variables de entorno (nunca en el repositorio):
//   CORREO_CONTACTO    dirección que recibe el formulario (obligatoria)
//   CORREO_REMITENTE   dirección desde la que sale el correo; por defecto, CORREO_CONTACTO
//   SMTP_HOST          servidor de correo saliente (obligatoria)
//   SMTP_PORT          puerto; por defecto 587
//   SMTP_SEGURIDAD     «tls» (STARTTLS, por defecto), «ssl» (TLS desde el principio) o «ninguna» (solo en local);
//                      con cualquier otro valor no se envía nada: falla cerrado, nunca en claro por error
//   SMTP_USUARIO / SMTP_CLAVE   credenciales, si el servidor las pide

declare(strict_types=1);

ini_set('display_errors', '0');

const LARGO_NOMBRE = 120;
const LARGO_CORREO = 254;
const LARGO_MENSAJE = 5000;

function configuracion(string $clave, string $defecto = ''): string
{
    $valor = getenv($clave);
    return ($valor === false || $valor === '') ? $defecto : $valor;
}

function texto_de(string $campo): string
{
    $valor = $_POST[$campo] ?? '';
    return is_string($valor) ? $valor : '';
}

/** Quita espacios y saltos de línea del principio y del final; devuelve null si no es UTF-8 válido. */
function recorta(string $texto): ?string
{
    if (preg_match('//u', $texto) !== 1) {
        return null;
    }
    return preg_replace('/^[\s\p{Z}]+|[\s\p{Z}]+$/u', '', $texto);
}

/**
 * Dirección que puede ir sin riesgo en una cabecera y en el sobre del correo: la forma sencilla de siempre (texto antes
 * de la @ separado por puntos, y dominio con letras, cifras, puntos y guiones). Rechaza lo que FILTER_VALIDATE_EMAIL
 * acepta y no hace falta en un formulario: la parte local entre comillas y los pares escapados, con los que se cuela un
 * salto de línea que abre una cabecera nueva en el correo, y las palabras codificadas (RFC 2047, «=?…?=»), que un lector
 * de correo decodifica a lo que lleven dentro, saltos de línea incluidos.
 */
function direccion_segura(string $direccion): bool
{
    $atomo = "[A-Za-z0-9!#$%&'*+\\/=?^_`{|}~-]+";
    return strlen($direccion) <= LARGO_CORREO
        && strpos($direccion, '=?') === false
        && preg_match("/\\A{$atomo}(?:\\.{$atomo})*@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\\z/D", $direccion) === 1
        && filter_var($direccion, FILTER_VALIDATE_EMAIL) !== false;
}

function escapa(string $texto): string
{
    return htmlspecialchars($texto, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

// --- Correo -----------------------------------------------------------------------------------------------------

function smtp_leer($conexion): array
{
    $texto = '';
    while (($linea = fgets($conexion, 1024)) !== false) {
        $texto .= $linea;
        if (strlen($linea) < 4 || $linea[3] !== '-') {
            return [(int) substr($linea, 0, 3), $texto];
        }
    }
    throw new RuntimeException('El servidor de correo no responde');
}

function smtp_orden($conexion, string $linea, array $esperados, string $paso): void
{
    if ($linea !== '') {
        fwrite($conexion, $linea . "\r\n");
    }
    [$codigo] = smtp_leer($conexion);
    if (!in_array($codigo, $esperados, true)) {
        throw new RuntimeException("SMTP {$codigo} en {$paso}");
    }
}

/** Entrega un correo de texto a un único destinatario. Solo el destino de la configuración entra en el sobre. */
function enviar_correo(string $destino, string $remitente, string $responder_a, string $asunto, string $cuerpo): void
{
    foreach ([$destino, $remitente, $responder_a] as $direccion) {
        if (!direccion_segura($direccion)) {
            throw new RuntimeException('Dirección de correo no válida');
        }
    }
    $servidor = configuracion('SMTP_HOST');
    if ($servidor === '') {
        throw new RuntimeException('SMTP_HOST sin definir');
    }
    $puerto = (int) configuracion('SMTP_PORT', '587');
    $seguridad = strtolower(trim(configuracion('SMTP_SEGURIDAD', 'tls')));
    if (!in_array($seguridad, ['tls', 'ssl', 'ninguna'], true)) {
        throw new RuntimeException('SMTP_SEGURIDAD tiene que ser tls, ssl o ninguna');
    }
    $usuario = configuracion('SMTP_USUARIO');
    $clave = configuracion('SMTP_CLAVE');

    $conexion = @stream_socket_client(
        ($seguridad === 'ssl' ? 'ssl://' : 'tcp://') . $servidor . ':' . $puerto,
        $codigo_error,
        $texto_error,
        10
    );
    if ($conexion === false) {
        throw new RuntimeException('No se pudo conectar con el servidor de correo');
    }
    stream_set_timeout($conexion, 15);

    try {
        $yo = preg_replace('/[^A-Za-z0-9.-]/', '', (string) gethostname()) ?: 'localhost';
        smtp_orden($conexion, '', [220], 'saludo');
        smtp_orden($conexion, "EHLO {$yo}", [250], 'EHLO');
        if ($seguridad === 'tls') {
            smtp_orden($conexion, 'STARTTLS', [220], 'STARTTLS');
            if (stream_socket_enable_crypto($conexion, true, STREAM_CRYPTO_METHOD_TLS_CLIENT) !== true) {
                throw new RuntimeException('No se pudo cifrar la conexión con el servidor de correo');
            }
            smtp_orden($conexion, "EHLO {$yo}", [250], 'EHLO tras STARTTLS');
        }
        if ($usuario !== '') {
            smtp_orden($conexion, 'AUTH LOGIN', [334], 'AUTH');
            smtp_orden($conexion, base64_encode($usuario), [334], 'usuario');
            smtp_orden($conexion, base64_encode($clave), [235], 'clave');
        }
        smtp_orden($conexion, "MAIL FROM:<{$remitente}>", [250], 'MAIL FROM');
        smtp_orden($conexion, "RCPT TO:<{$destino}>", [250, 251], 'RCPT TO');
        smtp_orden($conexion, 'DATA', [354], 'DATA');

        $dominio = substr($remitente, (int) strrpos($remitente, '@') + 1);
        $mensaje = implode("\r\n", [
            'Date: ' . date('r'),
            'From: =?UTF-8?B?' . base64_encode('El Archivo de Talavera') . "?= <{$remitente}>",
            "To: <{$destino}>",
            "Reply-To: <{$responder_a}>",
            'Subject: =?UTF-8?B?' . base64_encode($asunto) . '?=',
            'Message-ID: <' . bin2hex(random_bytes(12)) . "@{$dominio}>",
            'MIME-Version: 1.0',
            'Content-Type: text/plain; charset=UTF-8',
            'Content-Transfer-Encoding: base64',
            '',
            rtrim(chunk_split(base64_encode($cuerpo), 76, "\r\n")),
        ]);
        fwrite($conexion, preg_replace('/^\./m', '..', $mensaje) . "\r\n.\r\n");
        smtp_orden($conexion, '', [250], 'entrega');
        @fwrite($conexion, "QUIT\r\n");
    } finally {
        fclose($conexion);
    }
}

// --- Respuesta --------------------------------------------------------------------------------------------------

/**
 * Contesta con la página /contacto/ ya compilada, con el resultado en su sitio. En un error devuelve lo escrito al
 * formulario (si lo hay); en un envío correcto quita el formulario.
 */
function responde(int $estado, string $resultado, ?array $valores, bool $quitar_formulario = false): void
{
    http_response_code($estado);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-store');

    $pagina = @file_get_contents(__DIR__ . '/contacto/index.html');
    $marcador = '#<div id="resultado-envio"[^>]*></div>#';
    if ($pagina === false || preg_match($marcador, $pagina) !== 1) {
        echo '<!doctype html><html lang="es"><head><meta charset="utf-8">'
            . '<meta name="viewport" content="width=device-width, initial-scale=1">'
            . '<title>Contacto · El Archivo de Talavera</title></head><body><main>'
            . $resultado . '<p><a href="/contacto/">Volver al formulario</a></p></main></body></html>';
        return;
    }

    $pagina = preg_replace_callback($marcador, static fn (array $m): string => $resultado, $pagina, 1);

    if ($quitar_formulario) {
        $pagina = preg_replace('#<form\b.*?</form>#s', '<p><a class="boton" href="/">Volver al inicio</a></p>', $pagina, 1);
    } elseif ($valores !== null) {
        foreach (['nombre', 'correo'] as $campo) {
            $pagina = preg_replace_callback(
                '#<input\b[^>]*\bname="' . $campo . '"[^>]*>#',
                static fn (array $m): string => rtrim(substr($m[0], 0, -1), " /") . ' value="' . escapa($valores[$campo]) . '">',
                $pagina,
                1
            );
        }
        $pagina = preg_replace_callback(
            '#(<textarea\b[^>]*\bname="mensaje"[^>]*>)(</textarea>)#',
            static fn (array $m): string => $m[1] . escapa($valores['mensaje']) . $m[2],
            $pagina,
            1
        );
        if ($valores['privacidad']) {
            $pagina = preg_replace_callback(
                '#<input\b[^>]*\bname="privacidad"[^>]*>#',
                static fn (array $m): string => rtrim(substr($m[0], 0, -1), " /") . ' checked>',
                $pagina,
                1
            );
        }
    }
    echo $pagina;
}

function responde_error(int $estado, array $avisos, ?array $valores): void
{
    $lista = implode('', array_map(static fn (string $aviso): string => '<li>' . escapa($aviso) . '</li>', $avisos));
    responde($estado, '<div id="envio-error" class="aviso-envio error" role="alert"><ul>' . $lista . '</ul></div>', $valores);
}

function responde_correcto(): void
{
    responde(
        200,
        '<div id="envio-correcto" class="aviso-envio correcto" role="status"><p>Gracias, hemos recibido tu mensaje.</p></div>',
        null,
        true
    );
}

// --- Envío ------------------------------------------------------------------------------------------------------

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Location: /contacto/', true, 303);
    exit;
}

// El formulario nunca manda ficheros (no hay adjuntos mientras no se decida lo contrario): quien los manda es un
// robot o un cliente manipulado.
if (stripos($_SERVER['CONTENT_TYPE'] ?? '', 'multipart/') === 0 || !empty($_FILES)) {
    responde_error(422, ['Este formulario no admite archivos adjuntos.'], null);
    exit;
}

// Campo trampa: ninguna persona lo ve ni lo rellena. Se descarta sin avisar, con la misma confirmación de un envío normal.
$trampa = $_POST['web'] ?? '';
if (is_array($trampa) || trim((string) $trampa) !== '') {
    responde_correcto();
    exit;
}

$nombre = recorta(texto_de('nombre'));
$correo = recorta(texto_de('correo'));
$mensaje = recorta(texto_de('mensaje'));
$acepta = texto_de('privacidad') !== '';

$avisos = [];
if ($nombre === null || $nombre === '') {
    $avisos[] = 'Escribe tu nombre.';
} elseif (preg_match('/[\x00-\x1F\x7F]/', $nombre) === 1 || mb_strlen($nombre) > LARGO_NOMBRE) {
    $avisos[] = 'Escribe tu nombre en una sola línea y con ' . LARGO_NOMBRE . ' caracteres como mucho.';
}
if ($correo === null || $correo === '' || !direccion_segura($correo)) {
    $avisos[] = 'Escribe un correo válido, por ejemplo nombre@correo.es.';
}
if ($mensaje === null || $mensaje === '') {
    $avisos[] = 'Escribe tu mensaje.';
} elseif (
    preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', $mensaje) === 1
    // El navegador cuenta cada salto de línea como un carácter (maxlength) y lo envía como «\r\n»: se cuenta igual que él.
    || mb_strlen(preg_replace('/\r\n|\r|\n/', "\n", $mensaje)) > LARGO_MENSAJE
) {
    $avisos[] = 'El mensaje tiene caracteres no válidos o supera los ' . LARGO_MENSAJE . ' caracteres.';
}
if (!$acepta) {
    $avisos[] = 'Marca la casilla de la política de privacidad para poder enviar el mensaje.';
}

$valores = [
    'nombre' => texto_de('nombre'),
    'correo' => texto_de('correo'),
    'mensaje' => texto_de('mensaje'),
    'privacidad' => $acepta,
];

if ($avisos !== []) {
    responde_error(422, $avisos, $valores);
    exit;
}

$destino = configuracion('CORREO_CONTACTO');
$cuerpo = "Nombre: {$nombre}\r\nCorreo: {$correo}\r\n\r\nMensaje:\r\n"
    . preg_replace('/\r\n|\r|\n/', "\r\n", $mensaje) . "\r\n";

try {
    enviar_correo($destino, configuracion('CORREO_REMITENTE', $destino), $correo, 'Mensaje nuevo desde la web', $cuerpo);
} catch (Throwable $fallo) {
    // Solo el motivo técnico, nunca lo que escribió la visitante.
    error_log('contacto: ' . $fallo->getMessage());
    responde_error(502, ['No hemos podido enviar tu mensaje. Inténtalo de nuevo en unos minutos.'], $valores);
    exit;
}

responde_correcto();
