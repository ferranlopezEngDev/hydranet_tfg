"""Automated checks for the GUI-friendly workflow helpers."""

from pathlib import Path
import sys
import unittest

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.application import add_connection, add_node, create_empty_network
from src.gui.workflows import (
    build_model_curve_series,
    build_result_plot_payload,
    build_simulation_summary_text,
    get_registered_solver_method_help_text,
    get_registered_solver_method_options_template_text,
    get_connection_parameter_template,
    get_solver_configuration_help_text,
    list_registered_solver_methods,
    parse_json_mapping,
    parse_optional_float_sequence,
    parse_optional_string_sequence,
    run_simulation_for_gui,
)
from test.systems_testing import solve_parallel_pipes


class GuiWorkflowHelperTests(unittest.TestCase):
    """Keep the Tk-facing helper layer behaviorally stable."""

    def test_sequence_parsers_handle_empty_and_comma_separated_values(self) -> None:
        self.assertEqual(parse_optional_float_sequence(""), None)
        self.assertEqual(parse_optional_string_sequence(""), None)
        self.assertEqual(parse_optional_float_sequence("1.0, 2.5, -3"), (1.0, 2.5, -3.0))
        self.assertEqual(parse_optional_string_sequence("a, b , c"), ("a", "b", "c"))

    def test_parse_json_mapping_requires_one_object(self) -> None:
        mapping = parse_json_mapping('{"k": 10.0, "n": 2.0}')

        self.assertEqual(mapping["k"], 10.0)
        self.assertEqual(mapping["n"], 2.0)

        with self.assertRaises(ValueError):
            parse_json_mapping("[1, 2, 3]")

    def test_solver_method_templates_and_help_are_available(self) -> None:
        methods = list_registered_solver_methods("root")
        template_text = get_registered_solver_method_options_template_text(
            "root",
            "hybr",
        )
        template_mapping = parse_json_mapping(template_text)
        method_help = get_registered_solver_method_help_text("root", "hybr")
        configuration_help = get_solver_configuration_help_text()

        self.assertIn("hybr", methods)
        self.assertIn("lm", methods)
        self.assertIn("xtol", template_mapping)
        self.assertIn("maxfev", template_mapping)
        self.assertIn("SciPy root algorithm", configuration_help)
        self.assertTrue(method_help)

    def test_run_simulation_for_gui_builds_result_export_payload(self) -> None:
        system = solve_parallel_pipes.build_system()
        validation, result, result_export = run_simulation_for_gui(
            system,
            solver_name="root",
            solver_method_name="hybr",
            solver_tolerance_text="1e-8",
            solver_options_text='{"maxfev": 200}',
            node_ids_text="",
            initial_heads_text="95.0",
            update_nodes=True,
            problem_scale_text="1.0",
        )

        self.assertTrue(validation.is_valid)
        self.assertTrue(result.success)
        self.assertEqual(result.solver_method, "hybr")
        self.assertEqual(result.solver_options["maxfev"], 200)
        self.assertIn("solveResult", result_export)
        self.assertIn("nodeResults", result_export)
        self.assertIn("connectionResults", result_export)

    def test_run_simulation_for_gui_falls_back_for_missing_boundaries(self) -> None:
        system = create_empty_network()
        add_node(system, "n1", piezometric_head=100.0)
        add_node(system, "n2", piezometric_head=90.0)
        add_connection(
            system,
            "pipe",
            "fixed_kqn_pipe",
            "n1",
            "n2",
            params={"k": 1000.0, "n": 2.0},
        )

        validation, result, result_export = run_simulation_for_gui(
            system,
            solver_name="root",
            solver_method_name="hybr",
            solver_tolerance_text="",
            solver_options_text="",
            node_ids_text="",
            initial_heads_text="",
            update_nodes=True,
            problem_scale_text="1.0",
        )

        self.assertFalse(validation.is_valid)
        self.assertEqual(result.execution_mode, "current_state_evaluation")
        self.assertTrue(result.success)
        self.assertIn("strict policy", result.message)
        self.assertGreater(
            abs(result_export["connectionResults"]["pipe"]["flow_rate"]),
            0.0,
        )

    def test_run_simulation_for_gui_falls_back_when_all_heads_are_known(self) -> None:
        system = create_empty_network()
        add_node(system, "source", piezometric_head=100.0, is_boundary=True)
        add_node(system, "target", piezometric_head=92.0, is_boundary=True)
        add_connection(
            system,
            "pipe",
            "fixed_kqn_pipe",
            "source",
            "target",
            params={"k": 1000.0, "n": 2.0},
        )

        validation, result, result_export = run_simulation_for_gui(
            system,
            solver_name="root",
            solver_method_name="hybr",
            solver_tolerance_text="",
            solver_options_text="",
            node_ids_text="",
            initial_heads_text="",
            update_nodes=True,
            problem_scale_text="1.0",
        )

        self.assertTrue(validation.is_valid)
        self.assertEqual(result.execution_mode, "current_state_evaluation")
        self.assertIn("no unknown-head nodes", result.message)
        self.assertEqual(len(result_export["solveResult"]["node_ids"]), 2)

    def test_result_plot_payload_uses_framework_result(self) -> None:
        system = solve_parallel_pipes.build_system()
        _, result, _ = run_simulation_for_gui(
            system,
            solver_name="root",
            solver_method_name="hybr",
            solver_tolerance_text="",
            solver_options_text="",
            node_ids_text="",
            initial_heads_text="95.0",
            update_nodes=True,
            problem_scale_text="1.0",
        )

        title, categories, values, y_label = build_result_plot_payload(
            result,
            "connection_flows",
        )

        self.assertEqual(title, "Connection flow rates")
        self.assertEqual(y_label, "Flow rate Q")
        self.assertEqual(len(categories), 2)
        self.assertEqual(len(values), 2)

    def test_model_curve_series_can_sample_factor_polynomial(self) -> None:
        series = build_model_curve_series(
            "factor_polynomial",
            get_connection_parameter_template("factor_polynomial"),
            minimum_head_difference=-2.0,
            maximum_head_difference=2.0,
            sample_count=9,
            label="factor",
        )

        self.assertEqual(series.label, "factor")
        self.assertGreaterEqual(len(series.x_values), 2)
        self.assertEqual(len(series.x_values), len(series.y_values))

    def test_simulation_summary_text_reports_empty_state(self) -> None:
        summary = build_simulation_summary_text(None, None, None)

        self.assertIn("No simulation has been executed yet", summary)

    def test_simulation_summary_text_reports_current_state_mode(self) -> None:
        system = create_empty_network()
        add_node(system, "source", piezometric_head=100.0, is_boundary=True)
        add_node(system, "target", piezometric_head=92.0, is_boundary=True)
        add_connection(
            system,
            "pipe",
            "fixed_kqn_pipe",
            "source",
            "target",
            params={"k": 1000.0, "n": 2.0},
        )

        validation, result, result_export = run_simulation_for_gui(
            system,
            solver_name="root",
            solver_method_name="hybr",
            solver_tolerance_text="",
            solver_options_text="",
            node_ids_text="",
            initial_heads_text="",
            update_nodes=True,
            problem_scale_text="1.0",
        )
        summary = build_simulation_summary_text(validation, result, result_export)

        self.assertIn("Mode: Current-state evaluation", summary)
        self.assertIn("Method: hybr", summary)
        self.assertIn("Topology valid for solve: yes", summary)
        self.assertIn("Evaluated node heads: 2", summary)


if __name__ == "__main__":
    unittest.main()
