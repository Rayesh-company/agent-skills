from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_contracts", ROOT / "scripts" / "validate_contracts.py")
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class ContractValidationTests(unittest.TestCase):
    def test_repository_contracts_are_coherent(self) -> None:
        self.assertEqual([], validator.validate(ROOT))

    def test_missing_router_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory)
            (clone / "skills" / "router-rpm" / "agents").mkdir(parents=True)
            (clone / "skills" / "router-rpm" / "SKILL.md").write_text(
                "---\nname: router-rpm\ndescription: route\n---\n/cannot-exist-rpm\n",
                encoding="utf-8",
            )
            (clone / "skills" / "router-rpm" / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Router RPM"\n', encoding="utf-8"
            )
            (clone / "skill-inventory.json").write_text(
                '{"skills":["router-rpm"],"core_acceptance_skills":[],"router":"router-rpm"}',
                encoding="utf-8",
            )
            errors = validator.validate(clone)
            self.assertTrue(any("unknown skill" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
