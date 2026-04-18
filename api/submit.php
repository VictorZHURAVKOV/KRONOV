<?php
// ==========================================================================
// KRONOV — приём заявок с форм сайта
// Отправляет в Telegram + дубликат на email + лог в файл
// ==========================================================================

// Конфигурация
define('BOT_TOKEN', '8577704236:AAGmJPtl98XOzu19Z3rVKL4WbVhHDH_Mw_8');
define('TG_CHAT_ID', '8646091481');        // Алёна
define('EMAIL_TO',   'zhuravl_888@mail.ru');
define('EMAIL_FROM', 'no-reply@kronov.by');
define('LOG_FILE',   __DIR__ . '/leads.log');

// ---- CORS / method ----
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'method_not_allowed']);
    exit;
}

// ---- Parse input (JSON body OR form-data) ----
$raw = file_get_contents('php://input');
$input = [];
if ($raw) {
    $parsed = json_decode($raw, true);
    if (is_array($parsed)) $input = $parsed;
}
if (!$input && !empty($_POST)) $input = $_POST;

$name     = trim((string)($input['name']     ?? ''));
$phone    = trim((string)($input['phone']    ?? ''));
$source   = trim((string)($input['source']   ?? 'form'));
$details  = $input['details'] ?? '';
$comment  = trim((string)($input['comment']  ?? ''));
$time_pref= trim((string)($input['time']     ?? ''));
$ua       = substr($_SERVER['HTTP_USER_AGENT'] ?? '', 0, 200);
$ip       = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? '';

// Базовая валидация
$phone_digits = preg_replace('/\D/', '', $phone);
if (strlen($phone_digits) < 9) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'invalid_phone']);
    exit;
}

// Нормализация деталей в читаемый текст
$details_text = '';
if (is_array($details)) {
    $lines = [];
    foreach ($details as $k => $v) {
        if (is_array($v)) $v = json_encode($v, JSON_UNESCAPED_UNICODE);
        $lines[] = "$k: $v";
    }
    $details_text = implode("\n", $lines);
} else {
    $details_text = (string)$details;
}

// Время в Минске
date_default_timezone_set('Europe/Minsk');
$now_str = date('Y-m-d H:i');
$now_iso = date('c');

// Нормализация телефона для tel: и показа
$phone_clean = '+' . $phone_digits;
$phone_show  = $phone;

// ---- Лог (всегда, даже если Telegram/email упадут) ----
$log_entry = $now_iso . " | source=$source | name=" . str_replace("\n", " ", $name)
    . " | phone=$phone_clean | details=" . str_replace("\n", " | ", $details_text)
    . " | ip=$ip\n";
@file_put_contents(LOG_FILE, $log_entry, FILE_APPEND | LOCK_EX);

// ---- Сборка Telegram-сообщения ----
$esc = function($s) { return htmlspecialchars($s, ENT_QUOTES | ENT_HTML5, 'UTF-8'); };

$tg = "🏡 <b>Новая заявка — KRONOV</b>\n\n";
$tg .= "<b>Имя:</b> "     . ($name ? $esc($name) : '—') . "\n";
$tg .= "<b>Телефон:</b> <a href=\"tel:$phone_clean\">" . $esc($phone_show ?: $phone_clean) . "</a>\n";
$tg .= "<b>Источник:</b> " . $esc($source) . "\n";
if ($time_pref) $tg .= "<b>Удобное время:</b> " . $esc($time_pref) . "\n";
if ($comment)   $tg .= "<b>Комментарий:</b> "  . $esc($comment) . "\n";
if ($details_text) {
    $tg .= "\n<b>Детали:</b>\n<pre>" . $esc($details_text) . "</pre>\n";
}
$tg .= "\n<i>" . $esc($now_str) . " · Минск</i>";

// ---- Отправка в Telegram ----
$tg_ok = false;
$tg_err = null;
$ch = curl_init("https://api.telegram.org/bot" . BOT_TOKEN . "/sendMessage");
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => http_build_query([
        'chat_id' => TG_CHAT_ID,
        'text'    => $tg,
        'parse_mode' => 'HTML',
        'disable_web_page_preview' => true,
    ]),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 8,
    CURLOPT_SSL_VERIFYPEER => true,
]);
$tg_response = curl_exec($ch);
$tg_http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);
$tg_ok = ($tg_http === 200);
if (!$tg_ok) $tg_err = "HTTP $tg_http: " . substr((string)$tg_response, 0, 200);

// ---- Дубликат на email ----
$subj = "=?UTF-8?B?" . base64_encode("Заявка KRONOV — " . ($name ?: 'без имени') . " — $phone_clean") . "?=";
$body = "Новая заявка с сайта kronov.by\n\n";
$body .= "Имя:      " . ($name ?: '—') . "\n";
$body .= "Телефон:  $phone_clean\n";
$body .= "Источник: $source\n";
if ($time_pref) $body .= "Время:    $time_pref\n";
if ($comment)   $body .= "Коммент.: $comment\n";
if ($details_text) $body .= "Детали:\n  " . str_replace("\n", "\n  ", $details_text) . "\n";
$body .= "\nВремя заявки: $now_str (Минск)\nIP: $ip\nUA: $ua\n";

$headers = [
    "From: KRONOV Leads <" . EMAIL_FROM . ">",
    "Reply-To: " . EMAIL_FROM,
    "MIME-Version: 1.0",
    "Content-Type: text/plain; charset=UTF-8",
    "X-Mailer: KRONOV-Leads",
];
$email_ok = @mail(EMAIL_TO, $subj, $body, implode("\r\n", $headers));

// ---- Ответ ----
http_response_code(200);
echo json_encode([
    'ok'    => ($tg_ok || $email_ok),
    'tg'    => $tg_ok,
    'email' => $email_ok,
    'tg_err'=> $tg_ok ? null : $tg_err,
]);
