param(
    [switch]$SkipProcessor,
    [switch]$SkipUi
)

$ErrorActionPreference = "Stop"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Host ""
    Write-Host "==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Step failed: $Name"
    }
}

Set-Location $repoRoot

Run-Step "Python version" { & $python --version }

Run-Step "Compile Python sources" {
    & $python -m compileall app_settings.py core_logic.py hotkey_listener.py main_gui.py model_downloader.py engines tools
}

Run-Step "Route smoke tests" {
    & $python tools\route_smoke_test.py
}

Run-Step "Worker behavior tests" {
    & $python tools\worker_behavior_test.py
}

Run-Step "Threading lifecycle tests" {
    & $python tools\threading_lifecycle_test.py
}

Run-Step "Hotkey listener tests" {
    & $python tools\hotkey_listener_test.py
}

Run-Step "Import boundary tests" {
    & $python tools\import_boundary_test.py
}

Run-Step "Packaging profile tests" {
    & $python tools\packaging_profile_test.py
}

Run-Step "Runtime profile tests" {
    & $python tools\runtime_profile_test.py
}

Run-Step "App update tests" {
    & $python tools\app_updates_test.py
}

Run-Step "Whisper runtime detection tests" {
    & $python tools\whisper_runtime_detection_test.py
}

Run-Step "UI contrast static tests" {
    & $python tools\ui_contrast_static_test.py
}

Run-Step "UI transport state tests" {
    & $python tools\ui_transport_state_test.py
}

Run-Step "Preload model worker tests" {
    & $python tools\preload_model_worker_test.py
}

Run-Step "Release readiness audit" {
    & $python tools\release_readiness_audit.py
}

Run-Step "Release readiness audit tests" {
    & $python tools\release_readiness_audit_test.py
}

Run-Step "Artifact manifest audit" {
    & $python tools\artifact_manifest_audit.py
}

Run-Step "Open gate summary" {
    & $python tools\open_gate_summary.py --strict
}

Run-Step "Open gate summary tests" {
    & $python tools\open_gate_summary_test.py
}

Run-Step "Goal completion audit tests" {
    & $python tools\goal_completion_audit_test.py
}

Run-Step "Goal completion audit" {
    & $python tools\goal_completion_audit.py
}

Run-Step "Handoff next-action audit tests" {
    & $python tools\handoff_next_action_audit_test.py
}

Run-Step "Handoff next-action audit" {
    & $python tools\handoff_next_action_audit.py
}

Run-Step "Publication blocker audit tests" {
    & $python tools\publication_blocker_audit_test.py
}

Run-Step "Release status report tests" {
    & $python tools\release_status_report_test.py
}

Run-Step "Release decision matrix report tests" {
    & $python tools\release_decision_matrix_report_test.py
}

Run-Step "Release snapshot freshness audit tests" {
    & $python tools\release_snapshot_freshness_audit_test.py
}

Run-Step "Release snapshot freshness audit" {
    & $python tools\release_snapshot_freshness_audit.py
}

Run-Step "Release scope decision audit tests" {
    & $python tools\release_scope_decision_audit_test.py
}

Run-Step "Release scope decision audit" {
    & $python tools\release_scope_decision_audit.py
}

Run-Step "GitHub release preflight tests" {
    & $python tools\github_release_preflight_test.py
}

Run-Step "External gate orchestrator tests" {
    & $python tools\external_gate_orchestrator_test.py
}

Run-Step "External gate prerequisite audit tests" {
    & $python tools\external_gate_prerequisite_audit_test.py
}

Run-Step "External gate closure audit tests" {
    & $python tools\external_gate_closure_audit_test.py
}

Run-Step "Microphone evidence tooling tests" {
    & $python tools\microphone_evidence_tooling_test.py
}

Run-Step "Physical microphone gate runner tests" {
    & $python tools\physical_microphone_gate_test.py
}

Run-Step "Physical microphone run-card tests" {
    & $python tools\physical_microphone_run_card_test.py
}

Run-Step "Microphone gate report audit tests" {
    & $python tools\microphone_gate_report_audit_test.py
}

Run-Step "Final release tooling tests" {
    & $python tools\final_release_tooling_test.py
}

Run-Step "Final release gate audit tests" {
    & $python tools\final_release_gate_audit_test.py
}

Run-Step "Final public release gate runner tests" {
    & $python tools\final_public_release_gate_test.py
}

Run-Step "Alternative STT adapter tests" {
    & $python tools\alternative_stt_adapter_test.py
}

Run-Step "GGUF server contract tests" {
    & $python tools\gguf_contract_test.py
}

Run-Step "GGUF server probe tests" {
    & $python tools\gguf_server_probe_test.py
}

Run-Step "GGUF gate report audit tests" {
    & $python tools\gguf_gate_report_audit_test.py
}

Run-Step "GGUF real-server gate runner tests" {
    & $python tools\gguf_real_server_gate_test.py
}

Run-Step "Gemma model preflight tests" {
    & $python tools\gemma_model_preflight_test.py
}

Run-Step "Gemma E4B gate runner tests" {
    & $python tools\gemma_e4b_gate_test.py
}

Run-Step "Gemma E4B gate report audit tests" {
    & $python tools\gemma_e4b_gate_report_audit_test.py
}

Run-Step "Visual context smoke" {
    & $python tools\visual_context_smoke.py
}

Run-Step "Microphone capture diagnostic compile" {
    & $python -m py_compile tools\microphone_capture_diagnostic.py
}

Run-Step "External gate orchestrator compile" {
    & $python -m py_compile tools\external_gate_orchestrator.py
}

Run-Step "External gate prerequisite audit compile" {
    & $python -m py_compile tools\external_gate_prerequisite_audit.py
}

Run-Step "External gate closure audit compile" {
    & $python -m py_compile tools\external_gate_closure_audit.py
}

Run-Step "Physical microphone gate runner compile" {
    & $python -m py_compile tools\physical_microphone_gate.py
}

Run-Step "Physical microphone run-card compile" {
    & $python -m py_compile tools\physical_microphone_run_card.py
}

Run-Step "Microphone gate report audit compile" {
    & $python -m py_compile tools\microphone_gate_report_audit.py
}

Run-Step "GGUF real-server probe compile" {
    & $python -m py_compile tools\gguf_server_probe.py
}

Run-Step "GGUF gate report audit compile" {
    & $python -m py_compile tools\gguf_gate_report_audit.py
}

Run-Step "GGUF real-server gate runner compile" {
    & $python -m py_compile tools\gguf_real_server_gate.py
}

Run-Step "Gemma model preflight compile" {
    & $python -m py_compile tools\gemma_model_preflight.py
}

Run-Step "Gemma E4B gate runner compile" {
    & $python -m py_compile tools\gemma_e4b_gate.py
}

Run-Step "Gemma E4B gate report audit compile" {
    & $python -m py_compile tools\gemma_e4b_gate_report_audit.py
}

Run-Step "STT adapter benchmark compile" {
    & $python -m py_compile tools\stt_adapter_benchmark.py
}

Run-Step "Final release preflight compile" {
    & $python -m py_compile tools\final_release_preflight.py
}

Run-Step "Final release gate audit compile" {
    & $python -m py_compile tools\final_release_gate_audit.py
}

Run-Step "Final public release gate runner compile" {
    & $python -m py_compile tools\final_public_release_gate.py
}

Run-Step "Release readiness audit compile" {
    & $python -m py_compile tools\release_readiness_audit.py
}

Run-Step "Publication blocker audit compile" {
    & $python -m py_compile tools\publication_blocker_audit.py
}

Run-Step "Release status report compile" {
    & $python -m py_compile tools\release_status_report.py
}

Run-Step "Release decision matrix report compile" {
    & $python -m py_compile tools\release_decision_matrix_report.py
}

Run-Step "Release snapshot freshness audit compile" {
    & $python -m py_compile tools\release_snapshot_freshness_audit.py
}

Run-Step "Release scope decision audit compile" {
    & $python -m py_compile tools\release_scope_decision_audit.py
}

Run-Step "GitHub release preflight compile" {
    & $python -m py_compile tools\github_release_preflight.py
}

Run-Step "Goal completion audit compile" {
    & $python -m py_compile tools\goal_completion_audit.py
}

Run-Step "Handoff next-action audit compile" {
    & $python -m py_compile tools\handoff_next_action_audit.py
}

Run-Step "Open gate summary compile" {
    & $python -m py_compile tools\open_gate_summary.py
}

if (-not $SkipProcessor) {
    Run-Step "Gemma processor smoke" {
        & $python tools\gemma_processor_smoke_test.py
    }
}

if (-not $SkipUi) {
    Run-Step "Qt UI smoke" {
        $env:QT_QPA_PLATFORM = "offscreen"
        & $python tools\ui_smoke_test.py
    }
}

Write-Host ""
Write-Host "Quick verification gate passed."
