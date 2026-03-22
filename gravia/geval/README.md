# 🧪 Gravia G-Eval (Scientific Fact-Check)

## 📂 Overview
The `geval` module implements a high-fidelity validation pipeline for scientific reasoning. It follows the **LLM-as-a-judge** paradigm, using a high-parameter "Teacher" model to evaluate a "Student" model's outputs against a domain-specific Likert-scale rubric.

## 🎓 Theoretical Grounding & Citations

If you use this module in a publication, please cite the following foundational frameworks:

1.  **Core G-Eval Framework**:
    *   *Liu, Y., et al. (2023). G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment.*
    *   **DOI**: [10.48550/arXiv.2303.16634](https://doi.org/10.48550/arXiv.2303.16634)
    *   *Established the use of Chain-of-Thought (CoT) and Likert scales for LLM evaluation.*

2.  **LLM-as-a-Judge Paradigm**:
    *   *Zheng, L., et al. (2023). Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.*
    *   **DOI**: [10.48550/arXiv.2306.05685](https://doi.org/10.48550/arXiv.2306.05685)
    *   *The standard for using strong models to replace/augment human graders.*

3.  **Hallucination & Consistency (Self-CheckGPT)**:
    *   *Manakul, P., et al. (2023). SelfCheckGPT: Zero-Resource Hallucination Detection in Generative Language Models.*
    *   **DOI**: [10.48550/arXiv.2303.08896](https://doi.org/10.48550/arXiv.2303.08896)
    *   *The gold standard for zero-resource hallucination detection.*

4.  **Multimodal Context (Gemini 1.5)**:
    *   *Gemini Team, Google. (2024). Gemini 1.5: Unlocking multimodal understanding across millions of tokens of context.*
    *   **DOI**: [10.48550/arXiv.2403.05530](https://doi.org/10.48550/arXiv.2403.05530)
    *   *Relevant when utilizing long-context windows for fact-checking against massive neurophysiology datasets.*

## 📝 Methodology Phrasing
*"To validate the factual consistency of model outputs, we implemented a custom evaluation pipeline using the Gemini CLI. This framework utilizes a LLM-as-a-judge paradigm (Zheng et al., 2023) following the G-Eval protocol (Liu et al., 2023). Scientific accuracy was graded against a domain-specific rubric by a high-parameter teacher model, providing a quantitative metric for the subsequent Uncertainty-Weighted Distillation."*
