"""
Lightweight signature detection using PyMuPDF's native text extraction.
No OCR needed — reads the PDF text layer directly (instant, ~0 extra memory).
"""
import logging
import re
from typing import Dict, List, Optional
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


class EnhancedSignatureDetection:
    """Detect signatures using PyMuPDF text extraction — no OCR or ML required"""

    SIGNATURE_PATTERNS = [
        re.compile(r'(?:electronically\s+signed\s+by|digitally\s+signed\s+by)\s*[:\s]*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', re.IGNORECASE),
        re.compile(r'/s/\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', re.IGNORECASE),
    ]

    FIELD_KEYWORDS = re.compile(
        r'(?:borrower[\'s]*\s+signature|co-borrower[\'s]*\s+signature|'
        r'signature\s+of\s+\w+|sign(?:ature)?\s+here|'
        r'authorized\s+signature|notary\s+signature|'
        r'lender[\'s]*\s+signature|applicant[\'s]*\s+signature|'
        r'witness\s+signature|signed?\s+and\s+dated)',
        re.IGNORECASE
    )

    DATE_PATTERNS = [
        re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'),
        re.compile(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'),
        re.compile(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}', re.IGNORECASE),
    ]

    def detect_signature_fields(self, pdf_path: str) -> Dict:
        """
        Detect signatures using PyMuPDF native text + annotation extraction.
        Processes a 50-page PDF in under 1 second.
        """
        doc = fitz.open(pdf_path)

        signature_fields = []
        signatures_detected = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_idx = page_num + 1
            page_width = page.rect.width
            page_height = page.rect.height

            # 1. Check for PDF form widget annotations (signature fields)
            form_fields = self._extract_form_signature_fields(page, page_idx)
            signature_fields.extend(form_fields)

            # 2. Extract text blocks and search for signature keywords/patterns
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            page_text = page.get_text("text")

            # Find signature field labels in text blocks
            text_fields = self._find_signature_labels(text_dict, page_idx, page_width, page_height)
            signature_fields.extend(text_fields)

            # Find electronic/digital signature declarations
            e_sigs = self._find_electronic_signatures(page_text, text_dict, page_idx)
            signatures_detected.extend(e_sigs)

            # 3. Detect drawing-based signatures (ink annotations, line art)
            drawing_sigs = self._detect_drawing_signatures(page, page_idx)
            signatures_detected.extend(drawing_sigs)

        doc.close()

        # Deduplicate overlapping fields
        signature_fields = self._deduplicate(signature_fields)

        summary = self._generate_summary(signature_fields, signatures_detected)

        return {
            "signature_fields": signature_fields,
            "signatures_detected": signatures_detected,
            "summary": summary
        }

    def _extract_form_signature_fields(self, page, page_idx: int) -> List[Dict]:
        """Extract PDF form widget annotations that are signature fields"""
        fields = []
        for widget in page.widgets():
            if widget.field_type_string == "Signature" or (
                widget.field_name and re.search(r'sig', widget.field_name, re.IGNORECASE)
            ):
                rect = widget.rect
                fields.append({
                    "page": page_idx,
                    "field_type": "pdf_signature_field",
                    "label": widget.field_name or "Signature",
                    "is_filled": widget.field_value is not None and widget.field_value != "",
                    "coordinates": {
                        "x": int(rect.x0), "y": int(rect.y0),
                        "width": int(rect.width), "height": int(rect.height)
                    },
                    "nearby_text": ""
                })
        return fields

    def _find_signature_labels(self, text_dict: Dict, page_idx: int, page_w: float, page_h: float) -> List[Dict]:
        """Find text blocks containing signature keywords"""
        fields = []
        seen_y = set()

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:  # text block
                continue
            for line in block.get("lines", []):
                line_text = " ".join(span["text"] for span in line.get("spans", []))
                if self.FIELD_KEYWORDS.search(line_text):
                    bbox = line["bbox"]  # (x0, y0, x1, y1)
                    # Simple dedup by y-coordinate (within 5px)
                    y_key = round(bbox[1] / 5) * 5
                    if y_key in seen_y:
                        continue
                    seen_y.add(y_key)

                    field_type = self._classify_field_type(line_text)
                    fields.append({
                        "page": page_idx,
                        "field_type": field_type,
                        "label": line_text.strip()[:80],
                        "is_filled": False,  # will be updated if e-sig found nearby
                        "coordinates": {
                            "x": int(bbox[0]), "y": int(bbox[1]),
                            "width": int(bbox[2] - bbox[0]),
                            "height": int(bbox[3] - bbox[1])
                        },
                        "nearby_text": ""
                    })
        return fields

    def _find_electronic_signatures(self, page_text: str, text_dict: Dict, page_idx: int) -> List[Dict]:
        """Find electronic signature declarations like '/s/ John Doe' or 'Electronically signed by'"""
        signatures = []

        for pattern in self.SIGNATURE_PATTERNS:
            for match in pattern.finditer(page_text):
                signer_name = match.group(1).strip()
                if len(signer_name) < 3 or len(signer_name) > 60:
                    continue

                # Try to find bbox from text_dict
                coords = self._find_text_bbox(text_dict, match.group(0))

                # Extract nearby date
                context = page_text[max(0, match.start() - 150):min(len(page_text), match.end() + 150)]
                date = self._extract_date(context)

                signatures.append({
                    "page": page_idx,
                    "signer_name": signer_name,
                    "signature_type": "electronic",
                    "date": date,
                    "coordinates": coords
                })
        return signatures

    def _detect_drawing_signatures(self, page, page_idx: int) -> List[Dict]:
        """Detect ink annotations and dense line-art drawings that may be handwritten signatures"""
        signatures = []

        # Check ink annotations
        for annot in page.annots():
            if annot.type[0] == 15:  # Ink annotation
                rect = annot.rect
                signatures.append({
                    "page": page_idx,
                    "signer_name": "",
                    "signature_type": "handwritten",
                    "date": None,
                    "coordinates": {
                        "x": int(rect.x0), "y": int(rect.y0),
                        "width": int(rect.width), "height": int(rect.height)
                    }
                })

        # Check for dense vector drawings (paths) in signature-like regions
        drawings = page.get_drawings()
        if drawings:
            clusters = self._cluster_drawings(drawings, page.rect.height)
            for cluster in clusters:
                signatures.append({
                    "page": page_idx,
                    "signer_name": "",
                    "signature_type": "handwritten",
                    "date": None,
                    "coordinates": cluster
                })

        return signatures

    def _cluster_drawings(self, drawings: List, page_height: float) -> List[Dict]:
        """Cluster dense drawing paths that likely form a signature"""
        # Group paths that are close together and form signature-sized regions
        if len(drawings) < 5:
            return []

        rects = []
        for d in drawings:
            r = d.get("rect")
            if r:
                rects.append(fitz.Rect(r))

        if not rects:
            return []

        # Simple spatial clustering: merge overlapping/nearby rects
        clusters = []
        used = [False] * len(rects)

        for i, r in enumerate(rects):
            if used[i]:
                continue
            cluster_rect = fitz.Rect(r)
            used[i] = True
            # Expand and merge nearby rects
            for j in range(i + 1, len(rects)):
                if used[j]:
                    continue
                expanded = fitz.Rect(cluster_rect)
                expanded.x0 -= 10
                expanded.y0 -= 10
                expanded.x1 += 10
                expanded.y1 += 10
                if expanded.intersects(rects[j]):
                    cluster_rect |= rects[j]
                    used[j] = True

            # Signature-like: wider than tall, reasonable size
            w = cluster_rect.width
            h = cluster_rect.height
            if 30 < w < 400 and 10 < h < 150 and w > h * 0.8:
                clusters.append({
                    "x": int(cluster_rect.x0), "y": int(cluster_rect.y0),
                    "width": int(w), "height": int(h)
                })

        return clusters

    def _find_text_bbox(self, text_dict: Dict, search_text: str) -> Optional[Dict]:
        """Find the bounding box of a text fragment in the page"""
        search_lower = search_text.lower()[:40]
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                line_text = " ".join(span["text"] for span in line.get("spans", []))
                if search_lower in line_text.lower():
                    bbox = line["bbox"]
                    return {
                        "x": int(bbox[0]), "y": int(bbox[1]),
                        "width": int(bbox[2] - bbox[0]),
                        "height": int(bbox[3] - bbox[1])
                    }
        return None

    def _classify_field_type(self, text: str) -> str:
        if re.search(r'electronic|digital', text, re.IGNORECASE):
            return "electronic_signature"
        elif re.search(r'co-borrower|coborrower', text, re.IGNORECASE):
            return "co_borrower_signature"
        elif re.search(r'borrower', text, re.IGNORECASE):
            return "borrower_signature"
        elif re.search(r'notary', text, re.IGNORECASE):
            return "notary_signature"
        elif re.search(r'lender', text, re.IGNORECASE):
            return "lender_signature"
        elif re.search(r'witness', text, re.IGNORECASE):
            return "witness_signature"
        else:
            return "signature_field"

    def _extract_date(self, text: str) -> Optional[str]:
        for pattern in self.DATE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None

    def _deduplicate(self, fields: List[Dict], threshold: int = 20) -> List[Dict]:
        """Remove duplicate fields that overlap spatially"""
        if not fields:
            return fields
        unique = []
        for f in fields:
            c = f["coordinates"]
            is_dup = False
            for u in unique:
                uc = u["coordinates"]
                if (f["page"] == u["page"] and
                    abs(c["x"] - uc["x"]) < threshold and
                    abs(c["y"] - uc["y"]) < threshold):
                    is_dup = True
                    break
            if not is_dup:
                unique.append(f)
        return unique

    def _generate_summary(self, fields: List[Dict], signatures: List[Dict]) -> Dict:
        filled = sum(1 for f in fields if f.get('is_filled', False))
        electronic = sum(1 for s in signatures if s.get('signature_type') == 'electronic')
        handwritten = sum(1 for s in signatures if s.get('signature_type') == 'handwritten')
        return {
            "total_signature_fields": len(fields),
            "filled_fields": filled,
            "empty_fields": len(fields) - filled,
            "electronic_signatures": electronic,
            "handwritten_signatures": handwritten,
            "total_signatures_detected": len(signatures)
        }
