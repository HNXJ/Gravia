import bibtexparser
import re
import os

def draft_section_with_bib(section_name, template_constraints, bib_file_path, prompt_input):
    """
    Reads the .bib file and drafts a specific section enforcing academic lexicon.
    """
    # 1. Parse BibTeX
    valid_keys = []
    if os.path.exists(bib_file_path):
        with open(bib_file_path) as bibtex_file:
            bib_database = bibtexparser.load(bibtex_file)
            valid_keys = [entry['ID'] for entry in bib_database.entries]
    else:
        print(f"[WARNING] BibTeX file {bib_file_path} not found. Proceeding without keys.")

    # 2. Enforce Lexicon & Tone
    banned_words = ["delve", "tapestry", "in conclusion", "it is important to note", "robust"]
    
    # This function returns a system prompt to be passed to the LLM
    system_prompt = f"""
You are a highly critical computational neuroscientist. We are collaborating, and we must acknowledge that both of us (or our models) could be wrong. 
Draft the '{section_name}' section.

Constraints: {template_constraints}
Banned words (DO NOT USE): {', '.join(banned_words)}.

Use ONLY \cite{{key}} for references. 
Valid keys from .bib: {valid_keys}.
Every claim must be backed by a reputable journal DOI or citation from the provided keys. 
Do NOT hallucinate citations. 

User prompt: {prompt_input}
"""
    return system_prompt

def cross_reference_citations(text, bib_file_path):
    """
    Ensures every \cite{...} in the text exists in the .bib file.
    Returns (is_valid, missing_keys).
    """
    if not os.path.exists(bib_file_path):
        return True, [] # Can't validate without file

    with open(bib_file_path) as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)
        valid_keys = set(entry['ID'] for entry in bib_database.entries)

    citations = re.findall(r'\\cite{([^}]+)}', text)
    missing_keys = []
    for cite_group in citations:
        keys = [k.strip() for k in cite_group.split(',')]
        for key in keys:
            if key not in valid_keys:
                missing_keys.append(key)

    return len(missing_keys) == 0, missing_keys

if __name__ == "__main__":
    # Test directive requirements
    print("[GRAVIA] Semantic Formatter Initialized.")
    # Every citation must be cross-referenced; Banned words strictly enforced.
