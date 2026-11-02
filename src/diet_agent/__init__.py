"""Deterministic local assessment; recognition belongs to the calling agent."""
__version__ = "0.1.1"


def assess_diet(foods, requested_outputs=None, **kwargs):
    from .assessment import assess_diet as assess
    return assess(foods, requested_outputs=requested_outputs, **kwargs)
