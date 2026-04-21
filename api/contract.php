<?php
// ==========================================================================
// KRONOV — приём заявок на составление договора (с файлами)
// Шлёт в Telegram (sendMessage + sendDocument для каждого файла) + email.
// ==========================================================================

define('BOT_TOKEN', '8577704236:AAGmJPtl98XOzu19Z3rVKL4WbVhHDH_Mw_8');
define('TG_CHAT_ID', '8646091481');         // Алёна
define('EMAIL_TO',   'zhuravl_888@mail.ru');
define('EMAIL_FROM', 'no-reply@kronov.by');
define('LOG_FILE',   __DIR__ . '/contracts.log');
define('UPLOAD_DIR', __DIR__ . '/uploads/contracts');
define('MAX_FILE_MB', 8);
define('MAX_FILES', 5);
define('ALLOWED_EXT', ['jpg','jpeg','png','webp','heic','pdf']);

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok'=>false,'error'=>'method_not_allowed']); exit;
}

// Текстовые поля
$fio        = trim((string)($_POST['fio']       ?? ''));
$passport   = trim((string)($_POST['passport']  ?? ''));
$reg_addr   = trim((string)($_POST['reg_addr']  ?? ''));
$inst_addr  = trim((string)($_POST['inst_addr'] ?? ''));
$phone      = trim((string)($_POST['phone']     ?? ''));
$email      = trim((string)($_POST['email']     ?? ''));
$start_date = trim((string)($_POST['start_date']?? ''));
$pay_method = trim((string)($_POST['pay_method']?? ''));
$comment    = trim((string)($_POST['comment']   ?? ''));
$config     = trim((string)($_POST['config']    ?? ''));  // текст с конфигурацией из калькулятора
$total      = trim((string)($_POST['total']     ?? ''));

// Базовая валидация
$phone_digits = preg_replace('/\D/', '', $phone);
if (!$fio || strlen($phone_digits) < 9) {
    http_response_code(400);
    echo json_encode(['ok'=>false,'error'=>'missing_required_fields']); exit;
}
$phone_clean = '+' . $phone_digits;

// Каталог для файлов
if (!is_dir(UPLOAD_DIR)) @mkdir(UPLOAD_DIR, 0755, true);

// Сохраняем загруженные файлы
$saved_files = [];
$file_errors = [];
$max_bytes = MAX_FILE_MB * 1024 * 1024;
$req_id = date('Ymd-His') . '-' . substr(bin2hex(random_bytes(3)),0,6);

if (!empty($_FILES['files']) && is_array($_FILES['files']['name'])) {
    $cnt = count($_FILES['files']['name']);
    for ($i = 0; $i < $cnt && count($saved_files) < MAX_FILES; $i++) {
        if ($_FILES['files']['error'][$i] !== UPLOAD_ERR_OK) continue;
        $name = $_FILES['files']['name'][$i];
        $tmp  = $_FILES['files']['tmp_name'][$i];
        $size = (int)$_FILES['files']['size'][$i];
        if ($size <= 0 || $size > $max_bytes) { $file_errors[] = "$name: превышает " . MAX_FILE_MB . " МБ"; continue; }
        $ext = strtolower(pathinfo($name, PATHINFO_EXTENSION));
        if (!in_array($ext, ALLOWED_EXT)) { $file_errors[] = "$name: недопустимый формат"; continue; }
        $safe = $req_id . '_' . (count($saved_files)+1) . '.' . $ext;
        $dest = UPLOAD_DIR . '/' . $safe;
        if (move_uploaded_file($tmp, $dest)) {
            $saved_files[] = ['path'=>$dest,'orig'=>$name,'size'=>$size];
        } else {
            $file_errors[] = "$name: ошибка сохранения";
        }
    }
}

date_default_timezone_set('Europe/Minsk');
$now_str = date('Y-m-d H:i');
$now_iso = date('c');
$ip = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? '';

// Лог
$log = $now_iso . " | req=$req_id | fio=$fio | phone=$phone_clean | email=$email | files=" . count($saved_files) . " | ip=$ip\n";
@file_put_contents(LOG_FILE, $log, FILE_APPEND | LOCK_EX);

// --- Telegram сообщение ---
$esc = function($s){ return htmlspecialchars($s, ENT_QUOTES | ENT_HTML5, 'UTF-8'); };
$tg  = "📄 <b>Заявка на договор — KRONOV</b>\n";
$tg .= "<code>#$req_id</code>\n\n";
$tg .= "<b>ФИО:</b> " . $esc($fio) . "\n";
if ($passport)   $tg .= "<b>Паспорт:</b> " . $esc($passport) . "\n";
if ($reg_addr)   $tg .= "<b>Адрес регистрации:</b> " . $esc($reg_addr) . "\n";
if ($inst_addr)  $tg .= "<b>Адрес установки:</b> " . $esc($inst_addr) . "\n";
$tg .= "<b>Телефон:</b> <a href=\"tel:$phone_clean\">" . $esc($phone_clean) . "</a>\n";
if ($email)      $tg .= "<b>Email:</b> " . $esc($email) . "\n";
if ($start_date) $tg .= "<b>Желаемая дата:</b> " . $esc($start_date) . "\n";
if ($pay_method) $tg .= "<b>Оплата:</b> " . $esc($pay_method) . "\n";
if ($total)      $tg .= "<b>Итог калькулятора:</b> " . $esc($total) . "\n";
if ($comment)    $tg .= "\n<b>Комментарий:</b>\n" . $esc($comment) . "\n";
if ($config)     $tg .= "\n<b>Конфигурация:</b>\n<pre>" . $esc(mb_substr($config, 0, 2000)) . "</pre>\n";
$tg .= "\n<b>Файлов:</b> " . count($saved_files);
if ($file_errors) $tg .= "\n⚠️ Ошибки: " . $esc(implode('; ', $file_errors));
$tg .= "\n\n<i>" . $esc($now_str) . " · Минск</i>";

$tg_ok = false; $tg_err = null;
$ch = curl_init("https://api.telegram.org/bot" . BOT_TOKEN . "/sendMessage");
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => http_build_query([
        'chat_id'=>TG_CHAT_ID,
        'text'=>$tg,
        'parse_mode'=>'HTML',
        'disable_web_page_preview'=>true,
    ]),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 10,
]);
$resp = curl_exec($ch);
$http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
$tg_ok = ($http === 200);
if (!$tg_ok) $tg_err = "HTTP $http: " . substr((string)$resp, 0, 200);

// --- Telegram: отправка каждого файла как документа ---
$files_sent = 0;
foreach ($saved_files as $f) {
    if (!function_exists('curl_file_create')) break;
    $ch = curl_init("https://api.telegram.org/bot" . BOT_TOKEN . "/sendDocument");
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => [
            'chat_id' => TG_CHAT_ID,
            'document' => curl_file_create($f['path'], null, $f['orig']),
            'caption' => "📎 #$req_id — " . $f['orig'],
        ],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 30,
    ]);
    curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($code === 200) $files_sent++;
}

// --- Email дубль (без вложений — только текст, файлы лежат на сервере) ---
$subj = "=?UTF-8?B?" . base64_encode("Договор KRONOV — $fio — $phone_clean (#$req_id)") . "?=";
$body = "Заявка на договор с сайта kronov.by\nID: $req_id\n\n";
$body .= "ФИО:                 $fio\n";
if ($passport)  $body .= "Паспорт:             $passport\n";
if ($reg_addr)  $body .= "Адрес регистрации:   $reg_addr\n";
if ($inst_addr) $body .= "Адрес установки:     $inst_addr\n";
$body .= "Телефон:             $phone_clean\n";
if ($email)      $body .= "Email клиента:       $email\n";
if ($start_date) $body .= "Желаемая дата:       $start_date\n";
if ($pay_method) $body .= "Способ оплаты:       $pay_method\n";
if ($total)      $body .= "Итог калькулятора:   $total\n";
if ($config)     $body .= "\nКонфигурация:\n$config\n";
if ($comment)    $body .= "\nКомментарий:\n$comment\n";
$body .= "\nФайлов загружено: " . count($saved_files) . " (на сервере: " . UPLOAD_DIR . ")\n";
foreach ($saved_files as $f) $body .= "  - " . basename($f['path']) . "  (исх. " . $f['orig'] . ", " . round($f['size']/1024) . " КБ)\n";
$body .= "\nВремя: $now_str (Минск)\nIP: $ip\n";

$headers = [
    "From: KRONOV Leads <" . EMAIL_FROM . ">",
    "Reply-To: " . ($email ?: EMAIL_FROM),
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=UTF-8",
];
$email_ok = @mail(EMAIL_TO, $subj, $body, implode("\r\n", $headers));

http_response_code(200);
echo json_encode([
    'ok' => ($tg_ok || $email_ok),
    'req_id' => $req_id,
    'tg' => $tg_ok,
    'email' => $email_ok,
    'files_saved' => count($saved_files),
    'files_sent_to_tg' => $files_sent,
    'file_errors' => $file_errors,
    'tg_err' => $tg_ok ? null : $tg_err,
]);
