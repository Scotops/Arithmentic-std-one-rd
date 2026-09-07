param(
    [string]$Voice = 'Microsoft David Desktop',
    [string]$Suffix = 'local-context-20260907'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech

$root = Split-Path -Parent $PSScriptRoot
$locale = Join-Path $root 'content\i18n\en-US'
$textsPath = Join-Path $locale 'texts.json'
$audiosPath = Join-Path $locale 'audios.json'
$output = Join-Path $locale 'audio'
$texts = Get-Content -LiteralPath $textsPath -Raw | ConvertFrom-Json -AsHashtable
$audios = Get-Content -LiteralPath $audiosPath -Raw | ConvertFrom-Json -AsHashtable
$requiredNavigation = [ordered]@{
    'nav-page-tab-label' = 'Page list'
    'toc-title' = 'Contents'
}
foreach ($identifier in $requiredNavigation.Keys) {
    $texts[$identifier] = $requiredNavigation[$identifier]
    if (-not $audios.ContainsKey($identifier)) { $audios[$identifier] = "$identifier.mp3" }
}

function Get-SpokenText([string]$Identifier, [string]$Source) {
    $value = [System.Net.WebUtility]::HtmlDecode($Source)
    $value = $value -replace '<[^>]+>', ' '
    $value = $value -replace '\[\s*\]|_+', ' dash '
    $value = $value -replace '[−–]', ' minus '
    $value = $value -replace '\+', ' plus '
    $value = $value -replace '=', ' equals '
    $value = $value -replace '✅|❌', ' '
    $words = [ordered]@{
        'TIE' = 'T I E'; 'ICT' = 'I C T'; 'UDSM' = 'U D S M';
        'UDOM' = 'U D O M'; 'SQA' = 'S Q A'; 'ISBN' = 'I S B N';
        'MARUCo' = 'Maruco'
    }
    foreach ($word in $words.Keys) {
        $value = $value -replace "(?i)(?<!\w)$word(?!\w)", $words[$word]
    }
    return (($value -replace '\s+', ' ').Trim())
}

$trigger = '[+=−–÷×_]|(?<=\d)-(?=\d)|(?i)\b(TIE|ICT|UDSM|UDOM|SQA|ISBN|MARUCo)\b'
$candidates = [ordered]@{}
foreach ($identifier in $texts.Keys) {
    if (-not $audios.ContainsKey($identifier)) { continue }
    $source = [string]$texts[$identifier]
    $mapping = [string]$audios[$identifier]
    $isUnreviewedBaseClip = $mapping -match '^[^.]+\.mp3(?:\?.*)?$' -and $mapping -notmatch 'minus-voice'
    $isUnspokenBlank = $source.Trim() -eq '_'
    $isPendingVisibleText = $mapping -match '\.pending\.mp3$'
    $isRequiredNavigation = $requiredNavigation.Contains($identifier)
    if ((($source -match $trigger) -and ($isUnreviewedBaseClip -or $isUnspokenBlank)) -or $isRequiredNavigation -or $isPendingVisibleText) {
        $candidates[$identifier] = Get-SpokenText $identifier $source
    }
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = -1
try {
    foreach ($identifier in $candidates.Keys) {
        $filename = "$identifier.$Suffix.wav"
        $destination = Join-Path $output $filename
        $synth.SetOutputToWaveFile($destination)
        $synth.Speak([string]$candidates[$identifier])
        $synth.SetOutputToNull()
        if ((Get-Item -LiteralPath $destination).Length -lt 1000) {
            throw "Empty narration clip: $destination"
        }
        $audios[$identifier] = "$filename`?$Suffix"
    }
}
finally {
    $synth.Dispose()
}

$texts | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $textsPath -Encoding utf8
$audios | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $audiosPath -Encoding utf8
Write-Output "Generated $($candidates.Count) private on-device contextual narration clips with $Voice."
