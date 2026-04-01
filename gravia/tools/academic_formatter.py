import os

def generate_academic_latex(title, authors, abstract, content, references=None):
    """
    Enforces a strict, arXiv-compliant LaTeX template for academic manuscripts.
    """
    latex_template = r"""
\documentclass[twocolumn, 10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb, amsfonts}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{cite}
\usepackage{geometry}
\geometry{a4paper, margin=0.75in}

\title{""" + title + r"""}
\author{""" + authors + r"""}
\date{\today}

\begin{document}

\maketitle

\begin{abstract}
""" + abstract + r"""
\end{abstract}

\section{Introduction}
""" + content.get('introduction', '') + r"""

\section{Methods}
""" + content.get('methods', '') + r"""

\section{Results}
""" + content.get('results', '') + r"""

\section{Discussion}
""" + content.get('discussion', '') + r"""

\section{References}
""" + (references if references else "No references provided.") + r"""

\end{document}
"""
    return latex_template

def save_manuscript_tex(tex_content, file_path):
    """Saves the generated LaTeX content to a file, overwriting any existing one."""
    with open(file_path, 'w') as f:
        f.write(tex_content)
    print(f"Manuscript saved to {file_path}")

if __name__ == "__main__":
    # Test directive requirements
    print("[GRAVIA] Academic Formatter Initialized.")
    # Every citation must include a DOI; Tone must be critical computational neuroscientist.

