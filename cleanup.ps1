#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Cleanup script per il workspace nq-backtest.
    Rimuove file obsoleti: video già analizzati, scratch/, esperimenti falliti, legacy code.
    
.PARAMETER WhatIf
    Se specificato, mostra solo cosa verrebbe eliminato (DRY RUN sicuro).
    
.EXAMPLE
    .\cleanup.ps1 -WhatIf    # Anteprima - non elimina nulla
    .\cleanup.ps1             # Elimina per davvero

.NOTES
    Risparmio stimato: ~260MB (quasi tutto dai video MP4)
    Data creazione: 2026-07-08
#>

param([switch]$WhatIf)

$ROOT = "C:\Users\Mauro\Documents\nq-backtest"
$mode = if ($WhatIf) { "DRY RUN" } else { "LIVE DELETE" }
Write-Host "`n=== NQ-BACKTEST CLEANUP SCRIPT ===" -ForegroundColor Cyan
Write-Host "Modalita: $mode" -ForegroundColor $(if ($WhatIf) { "Yellow" } else { "Red" })
Write-Host ""

function Remove-SafeItem {
    param($Path, $Description)
    if (Test-Path $Path) {
        $size = if ((Get-Item $Path).PSIsContainer) {
            [math]::Round((Get-ChildItem $Path -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
        } else {
            [math]::Round((Get-Item $Path).Length / 1MB, 2)
        }
        Write-Host "  [$size MB] $Description" -ForegroundColor Gray
        Write-Host "           -> $Path" -ForegroundColor DarkGray
        if (-not $WhatIf) {
            Remove-Item -Recurse -Force $Path
            Write-Host "           ELIMINATO OK" -ForegroundColor Green
        }
    }
}

# ============================================================
# PRIORITA' ALTA: Video gia analizzati (~250MB)
# ============================================================
Write-Host "--- PRIORITA' ALTA: Video gia analizzati (~250MB) ---" -ForegroundColor Red

Remove-SafeItem "$ROOT\tmp_data\yt_DyS79Eb92Ug_full.mp4" "Video Fabio principale (analizzato, knowledge estratta)"
Remove-SafeItem "$ROOT\tmp_data\yt_DyS79Eb92Ug_s0_e600_final.mp4" "Clip video Fabio (analizzato)"
Remove-SafeItem "$ROOT\tmp_data\yt_DyS79Eb92Ug_s1200_e1800.mp4.part" "Download incompleto"
Remove-SafeItem "$ROOT\tmp_data\yt_test_crop.mp4" "Test crop"
Remove-SafeItem "$ROOT\tmp_data\yt_WayFFuTvgm0_full.mp4" "Video Fabio 2 (analizzato)"
Remove-SafeItem "$ROOT\tmp_data\yt_WayFFuTvgm0_s600_e963_final.mp4" "Clip video Fabio 2"
Remove-SafeItem "$ROOT\tmp_data\yt_xUyqIjCfZzg_s0_e1800_compressed.mp4" "Video Fabio 3 (analizzato)"
Remove-SafeItem "$ROOT\tmp_data\yt_xUyqIjCfZzg_s0_e600_compressed.mp4" "Clip video Fabio 3"

# ============================================================
# PRIORITA' ALTA: Cartella scratch/ (249 file, tutti one-shot)
# ============================================================
Write-Host "`n--- PRIORITA' ALTA: Cartella scratch/ (249 file) ---" -ForegroundColor Red

Remove-SafeItem "$ROOT\scratch" "INTERA cartella scratch/ - 249 script one-shot, nessun import dal main"

# ============================================================
# PRIORITA' MEDIA: Esperimenti mai integrati (DSPy, pydantic-ai)
# ============================================================
Write-Host "`n--- PRIORITA' MEDIA: Esperimenti falliti ---" -ForegroundColor Yellow

Remove-SafeItem "$ROOT\src\agents\dspy_llm_wrapper.py" "DSPy LLM wrapper - esperimento, non integrato"
Remove-SafeItem "$ROOT\src\agents\dspy_optimizer.py" "DSPy optimizer - esperimento, non integrato"
Remove-SafeItem "$ROOT\src\agents\fabio_dspy.py" "Fabio con DSPy - esperimento, non integrato"
Remove-SafeItem "$ROOT\src\agents\executor.py" "pydantic-ai executor - importato SOLO da run_backtest_v2.py"
Remove-SafeItem "$ROOT\src\agents\reflector.py" "asyncio reflector - nessun import dal main"
Remove-SafeItem "$ROOT\src\agents\fabio_agent.py.bak" "Backup file fabio_agent"

# ============================================================
# PRIORITA' MEDIA: Legacy / Superseded
# ============================================================
Write-Host "`n--- PRIORITA' MEDIA: Codice legacy/superseded ---" -ForegroundColor Yellow

Remove-SafeItem "$ROOT\run_backtest_v2.py" "Versione async OLD - rimpiazzata da run_backtest.py"
Remove-SafeItem "$ROOT\tg_capital_strategy.py" "Backtrader strategy - libreria obsoleta, mai usata in produzione"
Remove-SafeItem "$ROOT\mt5_tg_strategy.py" "Vecchia strategia MT5 - rimpiazzata da mt5_live_bot.py"
Remove-SafeItem "$ROOT\scripts\run_optimal_backtest_original.py" "Copia identica di run_optimal_backtest.py"

# ============================================================
# PRIORITA' BASSA: Script debug root-level
# ============================================================
Write-Host "`n--- PRIORITA' BASSA: Script debug root-level ---" -ForegroundColor Green

Remove-SafeItem "$ROOT\analyze_timestamps.py" "Debug script temporaneo"
Remove-SafeItem "$ROOT\debug_paths.py" "Debug paths"
Remove-SafeItem "$ROOT\simulate_v2.py" "Test v2 proposals (obsoleto)"
Remove-SafeItem "$ROOT\temp_check.py" "Temp check"
Remove-SafeItem "$ROOT\test_frontend.js" "Frontend test"
Remove-SafeItem "$ROOT\recover_v2_logs.py" "Recovery una-tantum (gia completata)"
Remove-SafeItem "$ROOT\scratch_analyze.py" "Scratch analisi root"
Remove-SafeItem "$ROOT\scratch_extract_crops.py" "Estrazione frame video (passato)"
Remove-SafeItem "$ROOT\scratch_extract_detail.py" "Estrazione dettagli frame"
Remove-SafeItem "$ROOT\scratch_extract_frames.py" "Estrazione frame"
Remove-SafeItem "$ROOT\scratch_inspect_json.py" "Debug JSON"
Remove-SafeItem "$ROOT\scratch_mfe.py" "MFE scratch"
Remove-SafeItem "$ROOT\scratch_print_chunk_trades.py" "Debug chunks"
Remove-SafeItem "$ROOT\scratch_search_candle_count.py" "Debug candle count"
Remove-SafeItem "$ROOT\scratch_search_trades.py" "Debug trades"
Remove-SafeItem "$ROOT\run_loop.py" "Semplice subprocess loop - raramente usato"

# ============================================================
# PRIORITA' BASSA: Output log obsoleti
# ============================================================
Write-Host "`n--- PRIORITA' BASSA: Output log obsoleti ---" -ForegroundColor Green

Remove-SafeItem "$ROOT\output\backtest_jan2026.log" "Log backtest gennaio 2026 (obsoleto)"
Remove-SafeItem "$ROOT\output\backtest_week2.txt" "Log week2 (obsoleto)"
Remove-SafeItem "$ROOT\output\session_v2_run.log" "Log sessione v2 (obsoleto)"

# Rimuove scratch_*.txt dall'output
Get-ChildItem "$ROOT\output" -Filter "scratch_*" | ForEach-Object {
    Remove-SafeItem $_.FullName "Output scratch file: $($_.Name)"
}

# ============================================================
# RIEPILOGO
# ============================================================
Write-Host "`n=== RIEPILOGO ===" -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "DRY RUN completato - nessun file eliminato." -ForegroundColor Yellow
    Write-Host "Per eliminare per davvero, esegui: .\cleanup.ps1" -ForegroundColor Yellow
} else {
    Write-Host "Cleanup completato!" -ForegroundColor Green
}

Write-Host "`nNOTA IMPORTANTE:" -ForegroundColor Magenta
Write-Host "  src\trade_manager.py usato da scripts\run_fst_scalp_backtest.py" -ForegroundColor Magenta
Write-Host "  Se non usi piu il Progetto 5 (FST Scalp), puoi eliminare entrambi manualmente." -ForegroundColor Magenta
Write-Host ""
