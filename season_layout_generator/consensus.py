"""Consensus computation and variant grouping.

Computes median consensus coordinates from multiple PDF analyses
and groups PDFs into layout variants when coordinate divergence
exceeds the configured threshold.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import fields

from season_layout_generator.models import (
    CanvasCoordinates,
    PageRegions,
    PdfAnalysisResult,
    VariantGroup,
)

# Maximum percentage-point difference before PDFs are considered different variants
DIVERGENCE_THRESHOLD: float = 5.0

# Field names on CanvasCoordinates used for coordinate comparison
_COORD_FIELDS: tuple[str, ...] = ("x", "y", "x2", "y2")

# Region field names on PageRegions (all CanvasCoordinates | None fields)
_REGION_FIELDS: tuple[str, ...] = tuple(
    f.name for f in fields(PageRegions)
)


def compute_consensus(results: list[PageRegions]) -> PageRegions:
    """Compute median consensus coordinates from multiple PageRegions.

    For each canvas region, collects all non-None coordinate values
    and takes the median of each (x, y, x2, y2).

    Args:
        results: List of PageRegions from multiple PDFs.

    Returns:
        A PageRegions with median coordinates for each detected region.

    Requirements: season-layout-generator 13.1, 13.2
    """
    region_values: dict[str, CanvasCoordinates | None] = {}

    for region_name in _REGION_FIELDS:
        coord_lists: dict[str, list[float]] = {c: [] for c in _COORD_FIELDS}

        for page_regions in results:
            coords: CanvasCoordinates | None = getattr(page_regions, region_name)
            if coords is not None:
                for coord_name in _COORD_FIELDS:
                    coord_lists[coord_name].append(getattr(coords, coord_name))

        if coord_lists["x"]:
            region_values[region_name] = CanvasCoordinates(
                x=statistics.median(coord_lists["x"]),
                y=statistics.median(coord_lists["y"]),
                x2=statistics.median(coord_lists["x2"]),
                y2=statistics.median(coord_lists["y2"]),
            )
        else:
            region_values[region_name] = None

    return PageRegions(**region_values)


def exceeds_divergence(
    regions: PageRegions,
    consensus: PageRegions,
    threshold: float = DIVERGENCE_THRESHOLD,
) -> bool:
    """Check if a PDF's regions diverge from the consensus beyond the threshold.

    Compares each coordinate of each region. If any single coordinate
    differs by more than the threshold, returns True.

    Args:
        regions: Regions from a single PDF.
        consensus: Current consensus regions for the variant group.
        threshold: Maximum allowed percentage-point difference.

    Returns:
        True if any coordinate exceeds the threshold.

    Requirements: season-layout-generator 14.1, 14.2
    """
    for region_name in _REGION_FIELDS:
        region_coords: CanvasCoordinates | None = getattr(regions, region_name)
        consensus_coords: CanvasCoordinates | None = getattr(consensus, region_name)

        if region_coords is None or consensus_coords is None:
            continue

        for coord_name in _COORD_FIELDS:
            diff = abs(
                getattr(region_coords, coord_name)
                - getattr(consensus_coords, coord_name)
            )
            if diff > threshold:
                return True

    return False


def _extract_scenario_id(filename: str) -> str:
    """Extract a scenario identifier from a chronicle PDF filename.

    Looks for patterns like "5-08", "Q14", or "1-00" in the filename.
    Falls back to the filename stem if no pattern matches.

    Args:
        filename: The PDF filename (basename only).

    Returns:
        The scenario identifier string.
    """
    match = re.search(r"(\d+-\d+|Q\d+)", filename)
    if match:
        return match.group(1)
    # Fallback: use filename without extension
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def group_variants(
    results: list[PdfAnalysisResult],
    threshold: float = DIVERGENCE_THRESHOLD,
) -> list[VariantGroup]:
    """Group PDF analysis results into layout variant groups.

    Processes results in order (assumed sorted by filename). The first
    PDF starts the first group. Each subsequent PDF is compared against
    the current group's running consensus. If it diverges beyond the
    threshold, a new group is started.

    Args:
        results: PDF analysis results, sorted by filename.
        threshold: Maximum allowed percentage-point difference.

    Returns:
        List of VariantGroup, each with its own consensus coordinates.

    Requirements: season-layout-generator 14.1, 14.2, 14.3, 14.4, 14.5
    """
    if not results:
        return []

    groups: list[list[PdfAnalysisResult]] = [[results[0]]]

    for result in results[1:]:
        current_group_regions = [r.regions for r in groups[-1]]
        consensus = compute_consensus(current_group_regions)

        if exceeds_divergence(result.regions, consensus, threshold):
            groups.append([result])
        else:
            groups[-1].append(result)

    return [
        VariantGroup(
            results=group,
            consensus=compute_consensus([r.regions for r in group]),
            first_scenario=_extract_scenario_id(group[0].filename),
        )
        for group in groups
    ]
