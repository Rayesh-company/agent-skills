from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from rayesh_runtime.state import new_run, save_run


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "rayesh.py"


class RayeshCliTests(unittest.TestCase):
    def run_cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_persisted_run_can_be_inspected_stopped_resumed_and_advanced(self):
        with TemporaryDirectory() as directory:
            started = self.run_cli(
                "start",
                "fix authentication bug",
                "--workflow",
                "bug-fix",
                "--runs-dir",
                directory,
            )
            payload = json.loads(started.stdout)
            run_id = payload["run_id"]
            self.assertEqual(payload["status"], "active")
            self.assertEqual(payload["frontier"], ["reproduce"])
            self.assertEqual(payload["graph"]["reproduce"]["type"], "agent")
            self.assertEqual(payload["next_transition"], "execute frontier: reproduce")
            self.assertTrue(Path(payload["state_path"]).exists())
            state = json.loads(Path(payload["state_path"]).read_text(encoding="utf-8"))
            self.assertTrue(state["canonical_state"]["state_agrees"])
            self.assertIn("git_head", state["canonical_state"])

            stopped = self.run_cli(
                "stop", run_id, "--runs-dir", directory, "--summary", "operator pause"
            )
            self.assertEqual(json.loads(stopped.stdout)["status"], "stopped")
            self.assertEqual(json.loads(stopped.stdout)["frontier"], [])

            resumed = self.run_cli("resume", run_id, "--runs-dir", directory)
            self.assertEqual(json.loads(resumed.stdout)["status"], "active")
            self.assertEqual(json.loads(resumed.stdout)["frontier"], ["reproduce"])

            claimed = self.run_cli("claim", run_id, "reproduce", "--runs-dir", directory)
            claimed_payload = json.loads(claimed.stdout)
            self.assertEqual(claimed_payload["running"], ["reproduce"])
            self.assertEqual(claimed_payload["execution"]["agent"]["role"], "reproducer")

            advanced = self.run_cli(
                "result",
                run_id,
                "reproduce",
                "--runs-dir",
                directory,
                "--verdict",
                "Accepted",
                "--criterion-evidence",
                "C1=artifacts/reproduction.md",
                "--criterion-evidence",
                "C2=artifacts/observations.md",
                "--criterion-verification",
                "C1=python -m unittest tests.test_reproduction",
                "--criterion-verification",
                "C2=manual observation review",
                "--critical-findings",
                "0",
                "--state-agrees",
            )
            self.assertEqual(json.loads(advanced.stdout)["frontier"], ["diagnose"])

            status = self.run_cli("status", run_id, "--runs-dir", directory)
            status_payload = json.loads(status.stdout)
            self.assertEqual(status_payload["nodes"]["reproduce"]["status"], "accepted")
            self.assertEqual(status_payload["nodes"]["reproduce"]["attempt"], 1)

    def test_failed_result_does_not_overwrite_the_run(self):
        with TemporaryDirectory() as directory:
            started = self.run_cli(
                "start",
                "fix authentication bug",
                "--workflow",
                "bug-fix",
                "--runs-dir",
                directory,
            )
            run_id = json.loads(started.stdout)["run_id"]
            failed = self.run_cli(
                "result",
                run_id,
                "reproduce",
                "--runs-dir",
                directory,
                "--verdict",
                "Accepted",
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Accepted requires", failed.stderr)

            status = self.run_cli("status", run_id, "--runs-dir", directory)
            node = json.loads(status.stdout)["nodes"]["reproduce"]
            self.assertEqual(node["status"], "pending")
            self.assertEqual(node["attempt"], 0)

    def test_concurrent_claims_are_serialized(self):
        workflow = {
            "metadata": {"name": "concurrent", "version": 1},
            "policies": {"max_parallel_agents": 1},
            "nodes": {
                node_id: {
                    "type": "agent",
                    "agent": {"role": node_id, "skills": ["tdd-rpm"]},
                    "acceptance": {"criteria": [f"{node_id} completes."]},
                }
                for node_id in ["first", "second"]
            },
        }
        with TemporaryDirectory() as directory:
            run = new_run("concurrency", workflow)
            save_run(run, Path(directory))
            commands = [
                [
                    sys.executable,
                    str(CLI),
                    "claim",
                    run["run_id"],
                    node_id,
                    "--runs-dir",
                    directory,
                ]
                for node_id in ["first", "second"]
            ]
            processes = [
                subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for command in commands
            ]
            results = [process.communicate() + (process.returncode,) for process in processes]
            self.assertEqual(sorted(result[2] for result in results), [0, 2])
            state_path = Path(directory) / run["run_id"] / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            running = [
                node_id
                for node_id, node_state in state["node_states"].items()
                if node_state["status"] == "running"
            ]
            self.assertEqual(len(running), 1)


if __name__ == "__main__":
    unittest.main()
