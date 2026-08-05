"""Evaluation-set construction. Ground truth is built here, never by the operational layer.

The package is named for what it builds so the layer-gold firewall is legible at the import line:
any `from src.goldset import ...` inside the operational layer is a firewall question on sight.
Nothing here runs while a query is being answered.
"""
