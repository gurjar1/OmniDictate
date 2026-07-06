from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _string_literals_in_list_assignment(source: str, target_name: str) -> list[str]:
    tree = ast.parse(source)
    values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == target_name for target in node.targets):
            continue
        if isinstance(node.value, ast.List):
            values.extend(element.value for element in node.value.elts if isinstance(element, ast.Constant) and isinstance(element.value, str))
    return values


class PackagingProfileTest(unittest.TestCase):
    def test_whisper_only_spec_keeps_pyav_available(self):
        spec_source = (ROOT / "OmniDictate.spec").read_text(encoding="utf-8")

        self.assertIn("collect_submodules('av')", spec_source)
        self.assertIn("collect_dynamic_libs('av')", spec_source)
        self.assertNotIn("'av',\n        'bitsandbytes'", spec_source)

    def test_whisper_only_spec_bakes_runtime_profile_hook(self):
        spec_source = (ROOT / "OmniDictate.spec").read_text(encoding="utf-8")
        hook_source = (ROOT / "pyi_runtime_whisper_only.py").read_text(encoding="utf-8")

        self.assertIn("runtime_hooks = ['pyi_runtime_whisper_only.py'] if whisper_only else []", spec_source)
        self.assertIn("runtime_hooks=runtime_hooks", spec_source)
        self.assertIn("OMNIDICTATE_PACKAGE_PROFILE", hook_source)
        self.assertIn("whisper-only", hook_source)

    def test_spec_still_excludes_heavy_experimental_stacks_from_whisper_profile(self):
        spec_source = (ROOT / "OmniDictate.spec").read_text(encoding="utf-8")
        direct_excludes = _string_literals_in_list_assignment(spec_source, "excludes")

        self.assertIn("matplotlib", direct_excludes)
        self.assertIn("'huggingface_hub'", spec_source)
        for package_name in ["torch", "transformers", "bitsandbytes", "cv2", "model_downloader"]:
            self.assertIn(package_name, spec_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
