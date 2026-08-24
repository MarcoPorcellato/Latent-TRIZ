"""Target-free bounded A0X-R1 activation extraction."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .a0x_a0_activations import A0XActivationError, ActivationArtifacts, _extract
from .a0x_contract import Leg


def extract_a0x_r1(
    *, adapter: Any, cases: Sequence[Mapping[str, Any]], selection: Mapping[str, Any],
    pair_binding: Mapping[str, Any], authorization_chain: Mapping[str, Any],
    output_dir: str | Path, created_at: str = "2026-08-24T00:00:00Z",
) -> ActivationArtifacts:
    """Extract only literal tuple index six and a separately descriptive final block."""
    return _extract(
        leg=Leg.R1, adapter=adapter, cases=cases, selection=selection, pair_binding=pair_binding,
        authorization_chain=authorization_chain,
        output_dir=output_dir, created_at=created_at, literal_indices=(6,),
        combinations={
            "problem_only": ("sentinel",),
            "problem_plus_transformation": ("mean_transformation_span",),
        },
    )


__all__ = ["A0XActivationError", "ActivationArtifacts", "extract_a0x_r1"]
