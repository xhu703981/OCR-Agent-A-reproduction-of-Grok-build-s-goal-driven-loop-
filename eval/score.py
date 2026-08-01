"""OCRoscope scorer — same family as institutional-books ocr_score_gen."""

from __future__ import annotations

from ocroscope import ocr_evaluation


def score_text(text: str, *, sid: str = "x") -> dict[str, float | None]:
    """
    Return OCR quality metrics for one string.

    ocr_quality: 0–100 higher = cleaner (OCRoscope ratio_segment)
    nonchar:     0–100 higher = more non-character junk
    ok:          False when OCRoscope aborts (too short / no lang signal)
    """
    if not text or not text.strip():
        return {"ocr_quality": None, "nonchar": None, "ok": False}
    est = ocr_evaluation(id=sid, text=text)
    est.calculate_ocr_rate()
    q, n = est.ratio_segment, est.ratio_nonchar
    if q is None or n is None:
        return {"ocr_quality": None, "nonchar": None, "ok": False}
    return {"ocr_quality": float(q), "nonchar": float(n), "ok": True}
