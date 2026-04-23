"""Backward-compatible entry point for the power-law comparison plot."""

try:
    from .plot_power_law_head_loss import main
except ImportError:
    from plot_power_law_head_loss import main


if __name__ == "__main__":
    main()
