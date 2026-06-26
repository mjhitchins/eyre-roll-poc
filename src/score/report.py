"""
Generate a markdown score report from one or more ScoreResult objects.

The report is the artefact the PhD application draws on. It must state:
  - the error rate plainly (never hide a high rate)
  - the normalisation applied (so the number is reproducible)
  - the membrane reference and ground-truth source
  - example error lines where available
"""

import datetime
from pathlib import Path
from typing import List, Optional

from .scorer import ScoreResult


def render_report(
    results: List[ScoreResult],
    model_id: str,
    prompt_version: str,
    notes: str = "",
    output_path: Optional[Path] = None,
) -> str:
    """
    Render a markdown report from a list of ScoreResult objects.

    Args:
        results:        one ScoreResult per membrane scored
        model_id:       identifier of the transcription model used
        prompt_version: version string of the transcription prompt
        notes:          free-text notes on error patterns, hand features, etc.
        output_path:    if given, write the report to this file

    Returns:
        the report as a markdown string
    """
    timestamp = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

    lines = [
        "# Transcription Score Report",
        "",
        f"Generated: {timestamp}",
        f"Model: `{model_id}`",
        f"Prompt version: `{prompt_version}`",
        f"Normalisation: {results[0].normalisation if results else 'n/a'}",
        "",
        "---",
        "",
        "## Results by membrane",
        "",
        "| Membrane | CER | WER | Ref words | Hyp words |",
        "|----------|-----|-----|-----------|-----------|",
    ]

    for r in results:
        mem = r.membrane_ref or "unknown"
        lines.append(
            f"| {mem} | {r.cer:.3f} | {r.wer:.3f} | {r.ref_words} | {r.hyp_words} |"
        )

    if len(results) > 1:
        avg_cer = sum(r.cer for r in results) / len(results)
        avg_wer = sum(r.wer for r in results) / len(results)
        lines += [
            "|----------|-----|-----|-----------|-----------|",
            f"| **Average** | **{avg_cer:.3f}** | **{avg_wer:.3f}** | | |",
        ]

    lines += [
        "",
        "---",
        "",
        "## Notes on errors",
        "",
        notes if notes else "_No notes recorded for this run._",
        "",
        "---",
        "",
        "## Methodology",
        "",
        "Ground truth: F. W. Maitland, *Pleas of the Crown for the County of Gloucester, 1221*",
        "(Internet Archive: `crowncountyplea00glouuoft`). Public domain.",
        "",
        "Membrane images: AALT (Anglo-American Legal Tradition, University of Houston).",
        "Crown copyright; viewed under educational use.",
        "",
        f"Normalisation applied before scoring: `{results[0].normalisation if results else 'n/a'}`",
        "",
        "CER = character error rate (Levenshtein edit distance / reference character count).",
        "WER = word error rate (Levenshtein edit distance at word level / reference word count).",
        "Both metrics can exceed 1.0 if the hypothesis is longer than the reference.",
        "",
        "> A high error rate on untuned multimodal transcription of 1221 court hand is an",
        "> expected and publishable finding. This report states it plainly.",
    ]

    report = "\n".join(lines) + "\n"

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    return report
