# Roda os prompts no Claude Code, isolado do repositório.
# Cada chamada de "claude -p" é uma conversa nova, sem memória das anteriores.

$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$exp = $PSScriptRoot
$saida = Join-Path $exp "saida\manual"
$isolado = "C:\temp\llm-isolado"
$bloqueadas = "Read,Bash,Glob,Grep,Edit,Write,NotebookEdit,WebFetch,WebSearch,Task"
$utf8SemBom = New-Object System.Text.UTF8Encoding $false

New-Item -ItemType Directory -Force $isolado | Out-Null
Set-Location $isolado   # pasta vazia: o Claude Code não enxerga o repositório

foreach ($base in "defeitos", "controle") {
    $prompt = Get-Content (Join-Path $exp "saida\prompt_$base.txt") -Raw -Encoding UTF8

    for ($i = 1; $i -le 5; $i++) {
        $arquivo = Join-Path $saida ("{0}_{1:D2}.txt" -f $base, $i)
        Write-Host "Rodando $base execucao $i..."

        $resposta = $prompt | claude -p --model opus --disallowedTools $bloqueadas | Out-String
        [System.IO.File]::WriteAllText($arquivo, $resposta, $utf8SemBom)

        Write-Host "  salvo em $arquivo ($($resposta.Length) caracteres)"
    }
}

Set-Location $exp
Write-Host "Concluido."