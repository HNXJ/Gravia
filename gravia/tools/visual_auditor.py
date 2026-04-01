import fitz
import os
import sys

# Add the workspace root to sys.path to allow importing from Computational
sys.path.append(os.path.expanduser("~/workspace/Computational"))
try:
    from eye.qwen_subagent import get_lms_vlm_query
except ImportError:
    print("[ERROR] Could not import eye.qwen_subagent. Ensure it exists in ~/workspace/Computational/eye/")

def audit_pdf_layout(pdf_path):
    """
    Converts PDF pages to images and audits them for layout issues using a local VLM.
    """
    if not os.path.exists(pdf_path):
        return False, f"Error: PDF file {pdf_path} not found."

    doc = fitz.open(pdf_path)
    audit_results = []
    passed_all = True

    # Check first 3 pages as per directive
    for page_num in range(min(3, len(doc))):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=150)
        img_path = f"temp_audit_p{page_num}.png"
        pix.save(img_path)

        prompt = (
            "Act as a strict journal editor. Analyze this academic paper page. "
            "Are there overlapping texts, figures bleeding into margins, or broken LaTeX math renderings? "
            "If perfect, reply 'PASS'. Otherwise, output ONLY structural critiques."
        )
        
        print(f"[AUDIT] Analyzing page {page_num+1}...")
        feedback = get_lms_vlm_query(img_path, query=prompt, min_tokens=1, max_tokens=200)

        os.remove(img_path)
        
        if "PASS" not in feedback:
            passed_all = False
            audit_results.append(f"Page {page_num+1} Issues: {feedback}")
        else:
            audit_results.append(f"Page {page_num+1}: PASS")

    if passed_all:
        return True, "All pages passed visual layout audit."
    else:
        return False, "\n".join(audit_results)

if __name__ == "__main__":
    # Test script if called directly
    if len(sys.argv) > 1:
        success, report = audit_pdf_layout(sys.argv[1])
        print(report)
    else:
        print("Usage: python visual_auditor.py <pdf_path>")
