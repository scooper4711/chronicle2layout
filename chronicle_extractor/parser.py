"""Scenario info extraction from PDF text.

Provides the ScenarioInfo dataclass and functions for extracting
scenario metadata. The primary method reads the chronicle sheet
(last page), falling back to page-header comparison for older PDFs.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioInfo:
    """Parsed scenario metadata from a PDF.

    Attributes:
        season: The season number (e.g., 1, 2). 0 for Quests.
        scenario: The zero-padded scenario number string (e.g., '07', '12').
        name: The scenario name as extracted from the PDF.
    """

    season: int
    scenario: str
    name: str


# Matches "Scenario #X-YY" or "#X–YY" (en-dash) on page 1 or chronicle.
SCENARIO_PATTERN: re.Pattern[str] = re.compile(r"#(\d+)[-–](\d+)")

# Matches "Quest #NN" on page 1 or chronicle.
QUEST_PATTERN: re.Pattern[str] = re.compile(r"Quest\s*#(\d+)", re.IGNORECASE)

_HEADER_LABEL = "pathfinder society scenario"

# Lines on the chronicle sheet that signal end of the name.
_CHRONICLE_STOP = {"adventure summary", "boons", "rewards", "purchases"}


def extract_from_chronicle(last_page_text: str) -> ScenarioInfo | None:
    """Extract scenario info from the chronicle sheet (last page).

    Newer PFS PDFs (Season 4+, Quests) have a clean chronicle header:
        Chronicle Code: XXXX
        Scenario #X-YY: Name  (or Quest #NN / Name on next line)
        Adventure Summary

    Args:
        last_page_text: Text content of the PDF's last page.

    Returns:
        A ScenarioInfo if the chronicle header is parseable, or None.

    Requirements: chronicle-extractor 3.1, 3.2, 3.3
    """
    lines = [line.strip() for line in last_page_text.split("\n")]
    lines = [line for line in lines if line]

    season = None
    scenario = None
    name_lines: list[str] = []
    found_number = False

    for line in lines:
        lower = line.lower()

        if lower in _CHRONICLE_STOP:
            break

        if lower.startswith("chronicle code"):
            continue

        if not found_number:
            # Try scenario pattern: "Scenario #X-YY:" or "Scenario #X-YY"
            s_match = SCENARIO_PATTERN.search(line)
            if s_match:
                season = int(s_match.group(1))
                scenario = s_match.group(2)
                # Name might be on the same line after the colon
                remainder = line[s_match.end():].strip().lstrip(":").strip()
                if remainder:
                    name_lines.append(remainder)
                found_number = True
                continue

            # Try quest pattern: "Quest #NN"
            q_match = QUEST_PATTERN.search(line)
            if q_match:
                season = 0
                scenario = q_match.group(1)
                remainder = line[q_match.end():].strip().lstrip(":").strip()
                if remainder:
                    name_lines.append(remainder)
                found_number = True
                continue
        else:
            name_lines.append(line)

    if season is None or scenario is None or not name_lines:
        return None

    return ScenarioInfo(
        season=season,
        scenario=scenario,
        name=" ".join(name_lines),
    )


def extract_scenario_number(first_page_text: str) -> tuple[int, str] | None:
    """Extract season and scenario number from first-page text.

    Tries the #X-YY scenario pattern first, then the Quest #NN pattern.

    Args:
        first_page_text: The full text content of the PDF's first page.

    Returns:
        A (season, scenario) tuple, or None if no match.
        Season is 0 for Quests.

    Requirements: chronicle-extractor 3.1, 3.2
    """
    match = SCENARIO_PATTERN.search(first_page_text)
    if match:
        return int(match.group(1)), match.group(2)

    q_match = QUEST_PATTERN.search(first_page_text)
    if q_match:
        return 0, q_match.group(1)

    return None


def _lines_after_header(page_text: str) -> list[str]:
    """Return non-empty stripped lines after the PFS header.

    Looks for "Pathfinder Society Scenario" or "Pathfinder Quest #NN".

    Args:
        page_text: Full text of a PDF page.

    Returns:
        Lines following the header, or an empty list if not found.
    """
    lines = [line.strip() for line in page_text.split("\n")]
    lines = [line for line in lines if line]

    for i, line in enumerate(lines):
        lower = line.lower()
        if lower.startswith(_HEADER_LABEL):
            return lines[i + 1:]
        if lower.startswith("pathfinder quest"):
            return lines[i + 1:]

    return []


def extract_scenario_name(
    page_a_text: str,
    page_b_text: str,
) -> str | None:
    """Extract the scenario name by finding common header lines.

    By comparing two interior pages, the common lines after the
    header are the scenario name.

    Args:
        page_a_text: Text of one interior page (e.g., page 3).
        page_b_text: Text of another interior page (e.g., page 4).

    Returns:
        The scenario name, or None if not found.

    Requirements: chronicle-extractor 3.3
    """
    lines_a = _lines_after_header(page_a_text)
    lines_b = _lines_after_header(page_b_text)

    if not lines_a or not lines_b:
        return None

    common: list[str] = []
    for la, lb in zip(lines_a, lines_b):
        if la == lb:
            common.append(la)
        else:
            break

    if not common:
        return None

    return " ".join(common)


def extract_name_from_chronicle(last_page_text: str) -> str | None:
    """Extract just the scenario name from the chronicle sheet.

    Handles chronicle sheets that don't contain a #X-YY number,
    such as "Pathfinder Society Intro: Name" format.

    Args:
        last_page_text: Text content of the PDF's last page.

    Returns:
        The scenario name, or None if not found.
    """
    lines = [line.strip() for line in last_page_text.split("\n")]
    lines = [line for line in lines if line]

    name_lines: list[str] = []
    past_header = False

    for line in lines:
        lower = line.lower()

        if lower in _CHRONICLE_STOP:
            break

        if lower.startswith("chronicle code"):
            past_header = True
            continue

        if not past_header:
            continue

        # Skip label lines that end with a colon (e.g., "Pathfinder Society Intro:")
        if line.endswith(":"):
            continue

        # Skip lines that are just the scenario/quest number
        if SCENARIO_PATTERN.search(line) or QUEST_PATTERN.search(line):
            continue

        name_lines.append(line)

    if not name_lines:
        return None

    return " ".join(name_lines)


def extract_scenario_info(
    first_page_text: str,
    page3_text: str | None = None,
    page4_text: str | None = None,
    page5_text: str | None = None,
    last_page_text: str | None = None,
) -> ScenarioInfo | None:
    """Extract PFS scenario info from PDF page text.

    Tries extraction methods in order of reliability:
    1. Chronicle sheet (last page) — cleanest, has both number and name
    2. Page 3+4 header comparison — works for Season 1-2
    3. Page 4+5 header comparison — works for Season 3

    Args:
        first_page_text: Text content of the PDF's first page.
        page3_text: Text of page 3 (optional).
        page4_text: Text of page 4 (optional).
        page5_text: Text of page 5 (optional).
        last_page_text: Text of the last page / chronicle sheet (optional).

    Returns:
        A ScenarioInfo if extraction succeeds, or None.

    Requirements: chronicle-extractor 3.1, 3.2, 3.3, 3.4
    """
    # Try chronicle sheet first (Season 4+, Quests)
    if last_page_text is not None:
        result = extract_from_chronicle(last_page_text)
        if result is not None:
            return result

    # Fall back to page 1 number + interior page name comparison
    number = extract_scenario_number(first_page_text)
    if number is None:
        return None

    season, scenario = number
    name = None

    if page3_text is not None and page4_text is not None:
        name = extract_scenario_name(page3_text, page4_text)

    if name is None and page4_text is not None and page5_text is not None:
        name = extract_scenario_name(page4_text, page5_text)

    # Last resort: chronicle has the name but not the number
    if name is None and last_page_text is not None:
        name = extract_name_from_chronicle(last_page_text)

    if name is None:
        return None

    return ScenarioInfo(season=season, scenario=scenario, name=name)
