#!/usr/bin/env bash
# Regenerate all debug_clips from a fixed set of chronicle PDFs.
set -euo pipefail

CLIP=".venv/bin/python clip_canvases.py"
PFS="Chronicles/pfs"

rm -rf debug_clips

$CLIP "$PFS/Bounties/B13-TheBlackwoodAbundanceChronicle.pdf"           debug_clips/Bounties-B13
$CLIP "$PFS/Quests/Q26-DragonsPleaChronicle.pdf"                       debug_clips/Quests-Q26
$CLIP "$PFS/Season 1/1-24-LightningStrikesStarsFallChronicle.pdf"      debug_clips/Season1-1-24
$CLIP "$PFS/Season 2/2-21-InPursuitofWaterChronicle.pdf"               debug_clips/Season2-2-21
$CLIP "$PFS/Season 3/3-17-DreamsofaDustboundIsleChronicle.pdf"         debug_clips/Season3-3-17
$CLIP "$PFS/Season 4/4-09-KillerintheGoldenMaskChronicle.pdf"         debug_clips/Season4-4-09
$CLIP "$PFS/Season 5/5-12-MischiefintheMazeChronicle.pdf"              debug_clips/Season5-5-12
$CLIP "$PFS/Season 6/6-01-YearofImmortalInfluenceChronicle.pdf"        debug_clips/Season6-6-01
$CLIP "$PFS/Season 7/7-01-EnoughisEnoughChronicle.pdf"                 debug_clips/Season7-7-01

echo "Done — all clips in debug_clips/"
