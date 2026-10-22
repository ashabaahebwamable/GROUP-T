"""Compatibility entry point for the evaluation runner.

The evaluation runner lives under ``scripts`` so test tooling and scenario
simulations are not part of the application source tree.
"""

from scripts.eval_runner import main


if __name__ == "__main__":
    raise SystemExit(main())
