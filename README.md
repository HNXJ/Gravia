# Composer v2.0: The Multi-Tool Research Factory

Composer is a unified workflow engine designed for high-fidelity scientific research, manuscript synthesis, and interactive presentations.

## 🛠️ Tool Suite

### 1. DeepRead (📖 Paper Analysis)
Automated Vision-Language extraction of facts, figures, and logic from PDFs.
- **Backend**: Utilizes the Office M3 Max (128GB) for remote inference.
- **Usage**:
  ```bash
  python3 composer.py read <path_to_paper.pdf>
  ```
- **Output**: Structured Markdown reports in `misc/papers/markdowns/`.

### 2. SlideTheater (🎬 Interactive Presentations)
Generates "Prezi-style" zooming presentations using `Reveal.js` and `Plotly`.
- **Theme**: Madelane Golden Dark (BastosLab standard).
- **Usage**:
  ```bash
  python3 composer.py slide --theme moon
  ```
- **Output**: Portable HTML decks in `slidetheater/export/html/`.

### 3. Writer (✍️ Manuscript Synthesis)
Transforms research Markdowns into formal documents.
- **Formats**: BioRxiv LaTeX and Microsoft Word (DOCX).
- **Usage**:
  ```bash
  python3 composer.py write <path_to_markdown>
  ```

## 🧠 Integrated Skills
Composer is self-documenting. Tool-specific intelligence is located in `.gemini/skills/` for autonomous guidance.

## 🚀 Directory Standards
- `src/`: Core Python engines.
- `content/`: (Ignored) Source data and Markdowns.
- `export/`: (Ignored) Final generated assets.

---
*Maintained by Hamed Nejat | Vanderbilt University*
