import json
import re
import logging
from pathlib import Path
from typing import Optional, Union, List, Dict
import mlx.core as mx
from mlx_lm import load, generate

logger = logging.getLogger("gravia.geval")

class GevalEngine:
    """G-Eval Scientific Fact-Check engine."""

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
        self._tokenizer = None

    def _ensure_model(self):
        if self._model is None:
            logger.info(f"🚀 Loading Teacher-Judge model: {self.model_path}")
            self._model, self._tokenizer = load(self.model_path)

    def fact_check(self, input_data: Union[str, Path, List[Dict]], rubric: Optional[str] = None) -> List[Dict]:
        """
        Perform a G-Eval scientific fact-check.
        
        Args:
            input_data: Either a path to a JSONL/MD file, a raw MD string, or a list of dicts.
            rubric: Optional custom rubric.
        """
        self._ensure_model()

        if rubric is None:
            rubric = """
You are an expert Neurophysiologist. Grade the following response on a scale of 1-5 based on:
1. Biophysical Accuracy: Does it honor Nernst/Goldman equations and circuit constraints?
2. Causal Logic: Does the mechanism follow a logical flow from synapse to network?
3. Factual Alignment: Are neurotransmitters and receptors correctly identified?

Output ONLY a JSON object: {"score": <int>, "reasoning": "<brief_explanation>"}
"""

        # 1. Resolve input records
        records = []
        if isinstance(input_data, (str, Path)):
            p = Path(input_data)
            if p.exists() and p.suffix == '.jsonl':
                with open(p, 'r') as f:
                    records = [json.loads(line) for line in f]
            elif p.exists() and p.suffix == '.md':
                with open(p, 'r') as f:
                    records = [{"content": f.read(), "source": str(p)}]
            else:
                # Treat as raw markdown content
                records = [{"content": str(input_data)}]
        elif isinstance(input_data, list):
            records = input_data

        results = []
        for record in records:
            text_to_eval = record.get("assistant") or record.get("content") or str(record)
            prompt = f"<|im_start|>system\n{rubric}<|im_end|>\n<|im_start|>user\nContent to Evaluate:\n{text_to_eval}<|im_end|>\n<|im_start|>assistant\n"
            
            logger.info("🧠 Grading content...")
            response = generate(self._model, self._tokenizer, prompt=prompt, max_tokens=500, verbose=False)
            
            # Extract JSON from teacher response
            try:
                # Look for JSON block
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    grade = json.loads(json_match.group())
                else:
                    grade = {"error": "No JSON found in response", "raw_output": response}
                
                results.append({**record, "fact_check": grade})
            except Exception as e:
                results.append({**record, "fact_check": {"error": str(e), "raw_output": response}})

        return results
