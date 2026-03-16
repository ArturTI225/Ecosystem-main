import unittest

from app.engine import run_student_code

TEST_LEVEL = {
    "id": "T-01",
    "goal": {"type": "reach_goal"},
    "grid": [
        "#####",
        "#S.G#",
        "#####",
    ],
    "start_dir": "E",
}


class RunnerEngineTests(unittest.TestCase):
    def test_reach_goal_success(self):
        result = run_student_code(
            level_id="T-01",
            student_code="move()\nmove()",
            level_spec=TEST_LEVEL,
            allowed_api=["move", "at_goal", "turn_left", "turn_right"],
            max_steps=20,
        )
        self.assertEqual(result["error_type"], "none")
        self.assertTrue(result["steps_used"] >= 2)

    def test_ast_import_blocked(self):
        result = run_student_code(
            level_id="T-01",
            student_code="import os\nmove()",
            level_spec=TEST_LEVEL,
            allowed_api=["move", "at_goal"],
            max_steps=20,
        )
        self.assertEqual(result["error_type"], "syntax")

    def test_hit_wall_runtime(self):
        result = run_student_code(
            level_id="T-01",
            student_code="turn_left()\nmove()",
            level_spec=TEST_LEVEL,
            allowed_api=["move", "turn_left"],
            max_steps=20,
        )
        self.assertEqual(result["error_type"], "runtime")
        self.assertEqual(result["primary_error"], "hit_wall")


if __name__ == "__main__":
    unittest.main()
