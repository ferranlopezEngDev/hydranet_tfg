from __future__ import annotations

import unittest

from hydranet import (
    CONTINUATION_SOLVER_NAME,
    Connection,
    Network,
    Node,
    PowerLawPipe,
    SolverConfig,
    evaluate_network,
    solve_network,
)
from hydranet.analysis import (
    build_connection_results_csv,
    build_diagnostics,
    build_model_samples_csv,
    build_model_samples_payload,
    build_node_results_csv,
    build_report_csv,
    build_scenario_csv,
    build_text_report,
    build_trace_csv,
    run_scenario_analysis,
    sample_model,
)


class AnalysisTests(unittest.TestCase):
    def _build_single_pipe_network(self) -> Network:
        network = Network(name="single_pipe")
        network.add_node(Node(id="source", head=100.0, is_boundary=True))
        network.add_node(Node(id="demand", head=95.0, demand=0.12))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="source",
                to_node="demand",
                model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
            )
        )
        return network

    def test_sample_model_generates_evenly_spaced_points(self) -> None:
        samples = sample_model(
            "power_law_pipe",
            {"coefficient": 1000.0, "exponent": 2.0},
            head_from=100.0,
            head_to_start=90.0,
            head_to_stop=100.0,
            samples=3,
        )

        self.assertEqual(len(samples), 3)
        self.assertAlmostEqual(samples[0].flow_rate, 0.1, places=9)
        self.assertAlmostEqual(samples[1].flow_rate, (5.0 / 1000.0) ** 0.5, places=9)
        self.assertAlmostEqual(samples[2].flow_rate, 0.0, places=12)
        payload = build_model_samples_payload(
            "power_law_pipe",
            {"coefficient": 1000.0, "exponent": 2.0},
            samples,
        )
        self.assertEqual(payload["model_type"], "power_law_pipe")
        self.assertIn("flow_rate", build_model_samples_csv(samples))

    def test_scenario_analysis_compares_against_baseline(self) -> None:
        comparison = run_scenario_analysis(
            self._build_single_pipe_network(),
            name="double_demand",
            demand_scale=2.0,
            solver_config=SolverConfig(
                solver_name=CONTINUATION_SOLVER_NAME,
                continuation_steps=3,
            ),
        )

        self.assertEqual(comparison.name, "double_demand")
        self.assertAlmostEqual(
            comparison.baseline_result.connection_flows["pipe_1"],
            0.12,
            places=9,
        )
        self.assertAlmostEqual(
            comparison.scenario_result.connection_flows["pipe_1"],
            0.24,
            places=9,
        )
        self.assertLess(
            comparison.scenario_result.node_heads["demand"],
            comparison.baseline_result.node_heads["demand"],
        )
        self.assertGreater(comparison.max_abs_head_delta, 0.0)
        self.assertGreater(comparison.max_abs_flow_delta, 0.0)
        self.assertIn("category", build_scenario_csv(comparison))

    def test_diagnostics_detect_negative_pressure_and_missing_result(self) -> None:
        network = Network(name="diagnostics")
        network.add_node(Node(id="source", head=10.0, is_boundary=True))
        network.add_node(Node(id="target", head=-1.0, is_boundary=True))
        network.add_connection(
            Connection(
                id="pipe_1",
                from_node="source",
                to_node="target",
                model=PowerLawPipe(coefficient=1000.0, exponent=2.0),
            )
        )

        no_result_items = build_diagnostics(network)
        self.assertTrue(any(item.severity == "info" for item in no_result_items))

        result = evaluate_network(network)
        negative_items = build_diagnostics(network, result=result)
        self.assertTrue(
            any("Negative pressure head" in item.message for item in negative_items)
        )

    def test_report_and_csv_exports_include_expected_headers(self) -> None:
        network = self._build_single_pipe_network()
        result = solve_network(network)
        diagnostics = build_diagnostics(network, result=result)

        report = build_text_report(network, result=result, diagnostics=diagnostics)
        report_csv = build_report_csv(network, result=result, diagnostics=diagnostics)
        node_csv = build_node_results_csv(result)
        connection_csv = build_connection_results_csv(result)
        trace_csv = build_trace_csv(result)

        self.assertIn("Hydranet MVP004 Report", report)
        self.assertIn("Hydraulic result", report)
        self.assertIn("section,key,value", report_csv)
        self.assertIn("pressure_head", node_csv)
        self.assertIn("flow_rate", connection_csv)
        self.assertIn("problem_scale", trace_csv)


if __name__ == "__main__":
    unittest.main()
