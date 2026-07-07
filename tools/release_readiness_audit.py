from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_DOCS = [
    "AGENTS.md",
    "docs/ai/COMPLETION_AUDIT.md",
    "docs/ai/DECISIONS.md",
    "docs/ai/HANDOFF.md",
    "docs/ai/LOOP.md",
    "docs/ai/STATE.md",
    "docs/ai/VERIFY.md",
    "docs/evidence/gemma-e4b-preflight-2026-07-05.md",
    "docs/specs/PRODUCT_SPEC.md",
    "docs/research/STT_MODEL_RESEARCH_2026.md",
    "docs/implementation-plans-and-checklists/phase-3-gemma-recovery.md",
    "docs/implementation-plans-and-checklists/phase-4-release-execution.md",
    "docs/release/ARTIFACT_MANIFEST_3.0.0-whisper.md",
    "docs/release/PUBLISHING_RUNBOOK_3.0.0.md",
    "docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md",
    "docs/release/RELEASE_NOTES_DRAFT_3.0.0-whisper.md",
    "docs/release/RELEASE_SCOPE_DECISIONS_3.0.0.md",
]


FORBIDDEN_README_PHRASES = [
    "Includes Python runtime and AI models",
    "Whisper needs roughly 4.5 GB",
]


FORBIDDEN_DOC_PHRASES = [
    "Moonshine-tiny spike did not beat Whisper",
    "did not beat the Whisper baseline on the current short fixture comparison",
    "because it did not beat Whisper on latency",
    "prints the four currently open external gates",
    "The tool reports the four current external gates",
    "open-gate summary now shows the one-command final public release gate",
    "final public artifact still has not been rebuilt",
    "Rebuild final public installer as `OmniDictate_Setup_v3.0.0.exe` after",
    "`preload_model_on_launch` is exposed in settings but not implemented",
]


FORBIDDEN_BASELINE_PACKAGES = [
    "accelerate",
    "bitsandbytes",
    "cv2",
    "model_downloader",
    "sentencepiece",
    "torch",
    "transformers",
]


FORBIDDEN_STAGED_PARTS = [
    "smoke_test_assets/",
    "models/",
    "models--",
    ".safetensors",
    ".gguf",
    ".onnx",
    ".bin",
    "CACHEDIR.TAG",
    ".locks/",
]


CANONICAL_RELEASE_REPORTS = [
    "smoke_test_assets\\packaging\\publication-blockers.json",
    "smoke_test_assets\\packaging\\release-status-report.json",
    "smoke_test_assets\\external-gate-prerequisites.json",
    "smoke_test_assets\\external-gate-closure-audit.json",
    "smoke_test_assets\\packaging\\release-decision-matrix.json",
    "smoke_test_assets\\packaging\\github-release-preflight.json",
    "smoke_test_assets\\external-gates-dry-run.json",
]


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.warnings: list[str] = []

    def fail(self, message: str) -> None:
        self.failures.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.fail(message)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _directory_size(path: Path) -> int:
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def _contains_all(text: str, snippets: list[str]) -> list[str]:
    return [snippet for snippet in snippets if snippet not in text]


def check_required_docs(audit: Audit) -> None:
    for rel_path in REQUIRED_DOCS:
        audit.require((ROOT / rel_path).is_file(), f"Missing required doc: {rel_path}")


def check_completion_audit(audit: Audit) -> None:
    text = _read("docs/ai/COMPLETION_AUDIT.md")
    required = [
        "Status: release objective locally ready",
        "Physical microphone phrase-match VAD/PTT",
        "Gemma E4B live weights",
        "Real GGUF server",
        "locally ready for publication",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"Completion audit missing required marker: {snippet}")
    for row_name in [
        "Verify physical microphone behavior",
        "Verify live Gemma E4B",
        "Verify real GGUF server route",
    ]:
        expected_state = "Complete" if row_name == "Verify physical microphone behavior" else "Incomplete"
        audit.require(
            f"| {row_name} |" in text and f"| {expected_state} |" in text,
            f"Completion audit must keep '{row_name}' at {expected_state}.",
        )


def check_release_checklist(audit: Audit) -> None:
    text = _read("docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md")
    required_open = [
        "- [x] Physical microphone phrase-match VAD and PTT both pass on real speech.",
        "physical_microphone_gate.py --model large-v3-turbo --duration 7 --countdown 3 --timeout 40 --device 1 --report-json",
        "microphone_capture_diagnostic.py --duration 7 --prompt --countdown 3",
        "microphone_capture_diagnostic.py --input smoke_test_assets\\microphone\\spoken-phrase-large-v3-turbo.wav --model large-v3-turbo --report-json",
        "live_microphone_smoke.py --model large-v3-turbo --mode both --timeout 40 --manual --countdown 3 --max-transcripts 1 --report-json",
        "Use the numeric `--device` index",
        "duplicated Windows",
        "rejects mismatched capture/live-loop device metadata",
        "microphone_gate_report_audit.py --capture-report smoke_test_assets\\microphone\\spoken-phrase-large-v3-turbo-report.json --loop-report",
        "- [x] Gemma 4 E4B is scoped out of the public Whisper-only `v3.0.0` release",
        "- [x] Real GGUF server support is scoped out of the public Whisper-only",
        "- [ ] Final GitHub release notes match the exact published artifact.",
        "Final public installer:",
        "324,505,897 bytes",
        "3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5",
        "Final Whisper-only bundle:",
    ]
    for snippet in _contains_all(text, required_open):
        audit.fail(f"Release checklist no longer shows open gate: {snippet}")

    required_closed = [
        "- [x] README package/model-download wording matches the verified Whisper-only",
        "- [x] Alternative STT adapter spike passed with Moonshine-tiny.",
        "- [x] Final public `OmniDictate_Setup_v3.0.0.exe` artifact gate passed",
        "- [x] Add publication blocker audit",
        "- [x] Rerun doc-slice `git diff --check` and `tools\\verify_local.ps1` after",
    ]
    for snippet in _contains_all(text, required_closed):
        audit.fail(f"Release checklist missing closed gate evidence: {snippet}")


def check_artifact_manifest(audit: Audit) -> None:
    text = _read("docs/release/ARTIFACT_MANIFEST_3.0.0-whisper.md")
    required = [
        "OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe",
        "B03A4BFA51CF363329FC47010A11F336E4F4D055DAB5E1C4EDF2B032DE0C8FEE",
        "OmniDictate_Setup_v3.0.0.exe",
        "3DD9CF5CD1E172D41208DDD3BDC3380A5A18BA1DDBA4BD5F3CE7FDEA2CEA10A5",
        "final-public-release-gate-report.json",
        "final-release-gate-report.json",
        "packaged-whisper-first-run.png",
        "916x719 RGB",
        "tools\\artifact_manifest_audit.py",
        "Total: 307.3 MB (322225944 bytes)",
        "package_profile: passed (whisper-only)",
        "Whisper model 'large-v3-turbo' loaded on cuda (float16).",
        "Route `Whisper only`, latency `0.60s`, 8/8",
        "The recommended public release tag is `v3.0.0`",
        "Final public artifact gate: passed",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"Artifact manifest missing current artifact evidence: {snippet}")

    notes = _read("docs/release/RELEASE_NOTES_DRAFT_3.0.0-whisper.md")
    audit.require("# OmniDictate v3.0.0" in notes, "Release notes must use a public title.")

    runbook = _read("docs/release/PUBLISHING_RUNBOOK_3.0.0.md")
    for snippet in [
        "Recommended public tag: `v3.0.0`",
        "OmniDictate_Setup_v3.0.0.exe",
        "3.0.0-whisper-release-smoke",
        "tools\\final_release_preflight.py",
        "tools\\final_public_release_gate.py",
        "tools\\final_release_gate_audit.py",
        "tools\\external_gate_orchestrator.py",
        "--microphone-device",
        "tools\\publication_blocker_audit.py",
        "tools\\release_status_report.py",
        "tools\\release_snapshot_freshness_audit.py",
        "GitHub preflight",
        "external-gate dry-run",
        "Scope: proven",
        "tools\\release_scope_decision_audit.py",
        "schema_version",
        "generated_at_utc",
        "scope_decisions_doc",
        "scope_gate_statuses",
        "open_gate_details",
        "pending` rows",
        "copy/pasteable selected-microphone numeric-index variant",
        "--microphone-device",
        "tools\\github_release_preflight.py",
        "scope_gate_statuses",
        "pending_release_scope_gates",
        "final-public-release-gate-report.json",
        "publication-blockers.json",
        "release-status-report.json",
        "github-release-preflight.json",
        "$env:OMNIDICTATE_PACKAGE_PROFILE='whisper-only'",
        "dist-whisper-final",
        "installer-whisper-final",
        "final-release-preflight.json",
        "final-release-gate-report.json",
    ]:
        audit.require(snippet in runbook, f"Publishing runbook missing versioning marker: {snippet}")


def check_release_notes_policy(audit: Audit) -> None:
    notes = _read("docs/release/RELEASE_NOTES_DRAFT_3.0.0-whisper.md")
    required = [
        "OmniDictate_Setup_v3.0.0.exe",
        "Local Whisper dictation with `large-v3-turbo` support.",
        "Smaller installer that downloads selected Whisper models on first use.",
        "**Check for Updates** button in Settings.",
        "**Transcribe Only** option",
        "Multi-language option.",
        "Minimum PTT hold setting",
        "Safer stop handling",
        "Python, Git, and PyTorch are not required",
        "Runtime** badge",
        "Performance Check",
        "NVIDIA Driver Downloads](https://www.nvidia.com/en-us/drivers/)",
        "CUDA runtime/toolkit version recommended by Performance Check",
        "CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive)",
        "cuDNN version recommended by Performance Check",
        "NVIDIA cuDNN Archive](https://developer.nvidia.com/rdp/cudnn-archive)",
        "Visual C++ Redistributable for Visual Studio 2015-2022 x64",
        "vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)",
        "Default dictation model: `large-v3-turbo`.",
        "%LOCALAPPDATA%\\OmniDictate\\unins000.exe",
    ]
    for snippet in _contains_all(notes, required):
        audit.fail(f"Release notes missing public release wording: {snippet}")
    forbidden = [
        "Gemma",
        "GGUF",
        "Experimental Source/Dev",
        "Moonshine",
        "Transformers/Torch",
        "source/dev",
        "release-policy",
    ]
    for snippet in forbidden:
        if snippet in notes:
            audit.fail(f"Release notes include internal wording: {snippet}")


def check_e4b_preflight_policy(audit: Audit) -> None:
    text = _read("docs/evidence/gemma-e4b-preflight-2026-07-05.md")
    required = [
        "E4B live gate remains open",
        "Local weights: missing",
        "--require-local --report-json smoke_test_assets\\gemma-e4b-preflight.json",
        "Transformers: available, version `5.5.0`",
        "Gemma model API: `AutoModelForMultimodalLM`",
        "CUDA: available",
        "tools\\gemma_model_preflight_test.py",
        "tools\\gemma_e4b_gate.py",
        "tools\\gemma_e4b_gate_report_audit.py",
        "--report-json smoke_test_assets\\gemma-e4b-gate-report.json",
        "--report-json smoke_test_assets\\gemma-e4b-live-smoke.json",
        "tools\\gemma_e4b_gate_report_audit_test.py",
        "Until that live smoke passes, E4B must remain labeled unverified",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"Gemma E4B preflight evidence missing boundary marker: {snippet}")


def check_gguf_real_server_policy(audit: Audit) -> None:
    text = _read("docs/evidence/gguf-real-server-runbook-2026-07-05.md")
    required = [
        "tools\\gguf_server_probe.py --url http://127.0.0.1:8080/v1",
        "--report-json smoke_test_assets\\gguf\\real-server-probe.json",
        "tools\\gguf_server_probe_test.py",
        "tools\\gguf_real_server_gate.py",
        "tools\\gguf_gate_report_audit.py",
        "--report-json smoke_test_assets\\gguf\\real-server-gate-report.json",
        "--report-json smoke_test_assets\\gguf\\real-server-smoke.json",
        "--server-implementation",
        "tools\\gguf_gate_report_audit_test.py",
        "raw audio is not sent",
        "does not close the real-server gate.",
        "This gate remains open until the commands above pass against a named real",
        "saved direct-probe and backend-smoke reports",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"GGUF real-server runbook missing boundary/report marker: {snippet}")


def check_stt_research_policy(audit: Audit) -> None:
    text = _read("docs/research/STT_MODEL_RESEARCH_2026.md")
    required = [
        "Keep `faster-whisper` plus Whisper `large-v3-turbo` as the default dictation",
        "Adapter Promotion Criteria",
        "at least 20% faster median inference",
        "Runtime isolation",
        "baseline `main_gui`/`core_logic` imports still avoid",
        "Packaging",
        "does not include the candidate model",
        "command, model id/version, latency, transcript",
        "tools\\stt_adapter_benchmark.py",
        "source, candidate Hugging Face cache footprint",
        "--audio-source physical-microphone",
        "moonshine-tiny-physical-mic.json",
        "candidate Hugging Face cache footprint",
        "package-boundary evidence",
        "baseline import-boundary",
        "optional command-routing checks",
        "candidate-meets-latency-promotion-bar",
        "defer-candidate-no-measured-win",
        "promotion_blockers",
        "`large-v3-turbo` median latency `0.47s`",
        "Moonshine-tiny median latency `0.31s`",
        "package-boundary `passed: true`",
        "import-boundary `passed: true`",
        "command-routing `comma` -> `,` and `period`",
        "`promotion_ready: false`",
        "promising follow-up",
        "NVIDIA Parakeet unified English or Nemotron 3.5 ASR",
        "Moonshine Streaming for low-latency edge dictation",
        "Qwen3-ASR, or GLM-ASR-Nano",
        "Voxtral Realtime",
        "VibeVoice-ASR, MOSS-Transcribe, Cohere Transcribe, and Gemma 4",
        "IBM Granite Speech 4.1 Plus",
        "2026-07-05 Live Source Refresh",
        "Low-latency dictation lane:",
        "Multilingual/dialect lane:",
        "Realtime/heavy lane:",
        "Rich-transcript lane:",
        "Hugging Face ASR models",
        "nvidia/nemotron-3.5-asr-streaming-0.6b",
        "mistralai/Voxtral-Mini-4B-Realtime-2602",
        "ibm-granite/granite-speech-4.1-2b-plus",
        "require a physical-microphone report",
        "fastest dictation engine",
        "too large and too new for the baseline package",
        "current global hotkey dictation release",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"STT research missing current model/release-policy marker: {snippet}")


def check_product_spec_policy(audit: Audit) -> None:
    text = _read("docs/specs/PRODUCT_SPEC.md")
    required = [
        "Alternative STT engines must stay behind adapter tooling",
        "Whisper-only package boundary",
        "Alternative STT Acceptance",
        "named evaluation lane",
        "low-latency dictation",
        "rich transcript",
        "Matches or beats `large-v3-turbo` accuracy",
        "Improves a named product metric",
        "Does not add eager heavy imports",
        "Does not add model files, candidate runtimes, or cache artifacts",
        "not default dictation replacements",
        "cache footprint, Windows warnings, and final keep/defer/reject decision",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"Product spec missing alternative-STT acceptance marker: {snippet}")


def check_phase4_release_execution(audit: Audit) -> None:
    text = _read("docs/implementation-plans-and-checklists/phase-4-release-execution.md")
    required = [
        "Phase 4 Release Execution Plan",
        "Status: ready for publication after physical microphone gate pass",
        "P4.1 - Physical Microphone Release Gate",
        "physical_microphone_gate.py --model large-v3-turbo",
        "Add `--device 8` with the intended numeric sounddevice input index",
        "Use a quoted",
        "must agree on device metadata",
        "P4.2 - Gemma E4B Release-Scope Decision",
        "tools\\gemma_e4b_gate.py",
        "E4B is explicitly scoped out of the public Whisper-only release",
        "P4.3 - Real GGUF Server Release-Scope Decision",
        "tools\\gguf_real_server_gate.py",
        "GGUF is explicitly scoped out of the public Whisper-only release",
        "P4.4 - Publication Decision",
        "tools\\publication_blocker_audit.py",
        "tools\\release_status_report.py",
        "tools\\release_snapshot_freshness_audit.py",
        "ignoring only `generated_at_utc`",
        "GitHub preflight JSON snapshots",
        "external-gate dry-run JSON snapshots",
        "tools\\release_scope_decision_audit.py",
        "explicitly scoped out",
        "publication_blocker_audit.py",
        "consumes those release-scope decisions",
        "selected-microphone dry-run guidance",
        "copy/pasteable",
        "numeric-index variant",
        "schema-versioned",
        "generated_at_utc",
        "detailed open-gate commands",
        "tools\\github_release_preflight.py",
        "scope_gate_statuses",
        "pending_release_scope_gates",
        "tools\\handoff_next_action_audit.py",
        "Scope: proven",
        "tools\\final_public_release_gate.py",
        "the installer is Whisper-only",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"Phase 4 release execution plan missing marker: {snippet}")


def check_canonical_release_report_references(audit: Audit) -> None:
    docs = {
        "docs/ai/HANDOFF.md": _read("docs/ai/HANDOFF.md"),
        "docs/ai/STATE.md": _read("docs/ai/STATE.md"),
        "docs/ai/VERIFY.md": _read("docs/ai/VERIFY.md"),
        "docs/release/PUBLISHING_RUNBOOK_3.0.0.md": _read("docs/release/PUBLISHING_RUNBOOK_3.0.0.md"),
    }
    joined_docs = "\n".join(docs.values())
    for report in CANONICAL_RELEASE_REPORTS:
        audit.require((ROOT / report).is_file(), f"Canonical release report is missing: {report}")
        audit.require(report in joined_docs, f"Canonical release report is not referenced in coordination docs: {report}")

    handoff = docs["docs/ai/HANDOFF.md"]
    for report in CANONICAL_RELEASE_REPORTS:
        audit.require(report in handoff, f"HANDOFF.md Exact Next Action must keep report refresh visible: {report}")


def check_readme_policy(audit: Audit) -> None:
    text = _read("README.md")
    required = [
        "Download And Install",
        "Fresh Windows Requirements",
        "Why The Installer Is Smaller Now",
        "Check for Updates",
        "Transcribe Only mode",
        "Minimum PTT hold",
        "Whisper models are downloaded on demand",
        "per-user installation under `%LOCALAPPDATA%\\OmniDictate`",
    ]
    for snippet in _contains_all(text, required):
        audit.fail(f"README missing public user wording: {snippet}")
    for phrase in ["Gemma", "GGUF", "Experimental Source/Dev Lanes", "Packaging policy"]:
        audit.require(phrase not in text, f"README contains internal release/research wording: {phrase}")
    for phrase in FORBIDDEN_README_PHRASES:
        audit.require(phrase not in text, f"README still contains stale phrase: {phrase}")


def check_forbidden_stale_phrases(audit: Audit) -> None:
    for rel_path in [
        "docs/ai/COMPLETION_AUDIT.md",
        "docs/ai/DECISIONS.md",
        "docs/ai/HANDOFF.md",
        "docs/ai/STATE.md",
        "docs/ai/VERIFY.md",
        "docs/release/RELEASE_NOTES_DRAFT_3.0.0-whisper.md",
        "docs/research/STT_MODEL_RESEARCH_2026.md",
    ]:
        text = _read(rel_path)
        for phrase in FORBIDDEN_DOC_PHRASES:
            audit.require(phrase not in text, f"{rel_path} still contains stale phrase: {phrase}")


def check_packaging_policy(audit: Audit) -> None:
    setup_text = _read("OmniDictate_Setup.iss")
    setup_required = [
        '#define DefaultDir "{localappdata}\\OmniDictate"',
        '#define PrivilegesRequiredMode "lowest"',
        '#define ArchitecturesInstallMode "x64compatible"',
        "PrivilegesRequired={#PrivilegesRequiredMode}",
    ]
    for snippet in _contains_all(setup_text, setup_required):
        audit.fail(f"Installer script missing per-user baseline marker: {snippet}")

    spec_text = _read("OmniDictate.spec")
    spec_required = [
        'package_profile = os.environ.get("OMNIDICTATE_PACKAGE_PROFILE", "full").strip().lower()',
        'whisper_only = package_profile in {"whisper", "whisper-only", "baseline"}',
        "runtime_hooks = ['pyi_runtime_whisper_only.py'] if whisper_only else []",
        "runtime_hooks=runtime_hooks",
        "if whisper_only:",
        "'torch'",
        "'transformers'",
        "'model_downloader'",
    ]
    for snippet in _contains_all(spec_text, spec_required):
        audit.fail(f"PyInstaller spec missing whisper-only packaging marker: {snippet}")

    gitignore_text = _read(".gitignore")
    for snippet in ["models/", "smoke_test_assets/", "*.safetensors", "*.gguf", "*.onnx"]:
        audit.require(snippet in gitignore_text, f".gitignore missing cache/artifact pattern: {snippet}")
    audit.require("/release/" in gitignore_text, ".gitignore should ignore only the root release artifact directory.")
    audit.require("release/" not in gitignore_text.replace("/release/", ""), ".gitignore has a broad release/ pattern.")


def check_git_hygiene(audit: Audit) -> None:
    try:
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", "docs/release/RELEASE_CHECKLIST_3.0.0-whisper.md"],
            cwd=ROOT,
            check=False,
        )
        audit.require(ignored.returncode != 0, "docs/release files are ignored by git; release docs would not be staged.")

        staged = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        audit.warn(f"Could not inspect git staging state: {exc}")
        return

    staged_paths = [line.strip().replace("\\", "/") for line in staged.stdout.splitlines() if line.strip()]
    forbidden = [
        path
        for path in staged_paths
        if any(part in path or path.endswith(part) for part in FORBIDDEN_STAGED_PARTS)
    ]
    audit.require(
        not forbidden,
        "Forbidden local artifact/model files are staged: " + ", ".join(forbidden),
    )


def check_optional_artifacts(audit: Audit, max_bundle_mb: float, max_installer_mb: float) -> None:
    bundle = ROOT / "smoke_test_assets/packaging/dist-whisper/OmniDictate"
    if bundle.exists():
        total = _directory_size(bundle)
        audit.require(
            total <= max_bundle_mb * 1024 * 1024,
            f"Whisper-only bundle is {total} bytes, above {max_bundle_mb:.1f} MB.",
        )
        internal = bundle / "_internal"
        if internal.exists():
            names = {child.name.lower() for child in internal.iterdir()}
            for package_name in FORBIDDEN_BASELINE_PACKAGES:
                audit.require(
                    package_name.lower() not in names,
                    f"Whisper-only bundle contains forbidden baseline package: {package_name}",
                )
        else:
            audit.warn("Whisper-only bundle exists but has no _internal directory to inspect.")
    else:
        audit.warn("Whisper-only bundle artifact not present; skipping local bundle audit.")

    installer = (
        ROOT
        / "smoke_test_assets/packaging/installer-whisper-release-smoke/OmniDictate_Setup_v3.0.0-whisper-release-smoke.exe"
    )
    if installer.exists():
        size = installer.stat().st_size
        audit.require(
            size <= max_installer_mb * 1024 * 1024,
            f"Whisper-only installer is {size} bytes, above {max_installer_mb:.1f} MB.",
        )
    else:
        audit.warn("Release-default installer artifact not present; skipping installer size audit.")

    screenshot = ROOT / "smoke_test_assets/ui/packaged-whisper-first-run.png"
    if not screenshot.exists():
        audit.warn("Packaged first-run screenshot artifact not present; skipping screenshot existence check.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit OmniDictate release-readiness claims against local evidence.")
    parser.add_argument("--max-bundle-mb", type=float, default=300.0)
    parser.add_argument("--max-installer-mb", type=float, default=300.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = Audit()

    check_required_docs(audit)
    check_completion_audit(audit)
    check_release_checklist(audit)
    check_artifact_manifest(audit)
    check_release_notes_policy(audit)
    check_e4b_preflight_policy(audit)
    check_gguf_real_server_policy(audit)
    check_stt_research_policy(audit)
    check_product_spec_policy(audit)
    check_phase4_release_execution(audit)
    check_canonical_release_report_references(audit)
    check_readme_policy(audit)
    check_forbidden_stale_phrases(audit)
    check_packaging_policy(audit)
    check_git_hygiene(audit)
    check_optional_artifacts(audit, args.max_bundle_mb, args.max_installer_mb)

    for warning in audit.warnings:
        print(f"WARN: {warning}")
    if audit.failures:
        for failure in audit.failures:
            print(f"FAIL: {failure}")
        return 1

    print("Release readiness audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
