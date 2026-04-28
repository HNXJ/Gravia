import sys
from pathlib import Path

def generate_presentation():
    extra_css = """
:root {
    --bastos-purple: #9400D3;
    --madelane-gold: #CFB87C;
    --gravia-white: #F5F5F5;
}
.reveal section {
    background-color: #000000 !important;
}
.gravia-element {
    position: absolute;
    transform: translate(-50%, -50%);
    width: max-content;
    text-align: center;
    color: var(--gravia-white);
    font-weight: 400;
}
.gravia-title {
    color: var(--madelane-gold);
    font-weight: 700;
    text-transform: uppercase;
}
.gravia-global-footer {
    position: fixed;
    left: 50%;
    top: 95%;
    transform: translate(-50%, -50%);
    color: var(--madelane-gold);
    font-size: 14px;
    letter-spacing: 3px;
    font-weight: 400;
    z-index: 1000;
}
h1, h2, h3, h4, h5, h6 {
    font-weight: 400 !important;
}
h1.gravia-title, h2.gravia-title {
    font-weight: 700 !important;
}
"""

    def get_style(loc):
        x, y = loc
        return f"position: absolute; left: {x*100}%; top: {y*100}%; transform: translate(-50%, -50%); width: max-content; text-align: center;"

    def get_iframe_style(loc):
        x, y = loc
        if x == 0.5 and y == 0.5:
            w, h = 900, 450
        else:
            w, h = 500, 450
        return f"position: absolute; left: {x*100}%; top: {y*100}%; transform: translate(-50%, -50%); width: {w}px; height: {h}px; border: none; background: transparent; overflow: hidden;"

    manifest = [
        {
            "title": ("Omission Mismatch Prediction Error & Underlying Neurophysiology", [0.5, 0.45]),
            "subtitle": ("Presenter: Hamed Nejat", [0.5, 0.6]),
        },
        {
            "title": ("The MaDeLaNe-MaDeLaMo Closed-Loop", [0.5, 0.1]),
            "figure": ("./f001.html", [0.5, 0.5]),
            "body": ("Reverse-engineering the generative model of the primate cortex.", [0.5, 0.85]),
        },
        {
            "title": ("Conceptual Framework: Active Inference & Routing", [0.5, 0.5]),
            "body": ("Predictive coding: Minimize mismatch to survive.", [0.5, 0.6]),
        },
        {
            "title": ("Chapter 1: Computational Biophysics", [0.5, 0.45]),
            "body": ("Modelling & Tuning Framework", [0.5, 0.55]),
        },
        {
            "title": ("Laminar Circuit Architecture", [0.5, 0.1]),
            "figure": ("./f002.html", [0.3, 0.5]),
            "body": ("Implementation of Hodgkin-Huxley networks featuring PV, SST, and VIP motifs.", [0.7, 0.5]),
        },
        {
            "title": ("Jaxley: Differentiable Simulation", [0.5, 0.1]),
            "body": ("Solving the inverse problem of synaptic conductances via JAX.", [0.5, 0.4]),
            "figure": ("./f003.html", [0.5, 0.65]),
        },
        {
            "title": ("Genetic-Stochastic-Delta-Rule (GSDR)", [0.5, 0.1]),
            "figure": ("./f004.html", [0.5, 0.5]),
            "body": ("Self-supervised evolutionary tuning of network oscillations.", [0.5, 0.85]),
        },
        {
            "title": ("E-I Balance & Rhythmic Benefits", [0.5, 0.1]),
            "figure": ("./f005.html", [0.5, 0.5]),
            "body": ("Computational advantages of rhythmic predictive routing.", [0.5, 0.85]),
        },
        {
            "title": ("Chapter 2: In-Vivo Paradigm", [0.5, 0.45]),
            "body": ("MaDeLaNe Primate Neurophysiology", [0.5, 0.55]),
        },
        {
            "title": ("The Ghost Signal Paradigm", [0.5, 0.1]),
            "figure": ("./f006.html", [0.5, 0.5]),
            "body": ("AAAB vs. AXAB: Isolating prediction error from sensory deviance.", [0.5, 0.85]),
        },
        {
            "title": ("Multi-Area Dense Neurophysiology", [0.5, 0.1]),
            "figure": ("./f007.html", [0.3, 0.5]),
            "body": ("11 Areas Sampled: V1, V2, V4, MT, MST, TEO, FST, FEF, PFC.", [0.7, 0.5]),
        },
        {
            "title": ("The Sparse-Global Paradox", [0.5, 0.1]),
            "body": [
                ("Sparse Units Show Omission Spiking (FEF/PFC)", [0.25, 0.5]),
                ("Global Inhibition of Alpha/Beta Power", [0.75, 0.5]),
            ],
        },
        {
            "title": ("Chapter 3: In-Silico Paradigm", [0.5, 0.45]),
            "body": ("MaDeLaMo Cortical Column Model", [0.5, 0.55]),
        },
        {
            "title": ("The 2-Column V1-PFC Matrix", [0.5, 0.1]),
            "figure": ("./f008.html", [0.5, 0.5]),
            "body": ("Sensory to Executive Synthesis.", [0.5, 0.85]),
        },
        {
            "title": ("Mechanism: Top-Down Gain Control", [0.5, 0.1]),
            "figure": ("./f009.html", [0.5, 0.5]),
            "body": ("How sparse higher-order spikes drive global field suppression.", [0.5, 0.85]),
        },
        {
            "title": ("Validation via RSA & SSS", [0.5, 0.1]),
            "figure": ("./f010.html", [0.5, 0.5]),
            "body": ("Maximizing representational similarity between empirical data and model.", [0.5, 0.85]),
        },
        {
            "title": ("Active Inference & Future Directions", [0.5, 0.1]),
            "body": ("Clinical applications in interneuron-deficit pathologies.", [0.5, 0.5]),
        },
        {
            "title": ("Questions & Acknowledgments", [0.5, 0.5]),
        }
    ]

    slides_html = ""
    for i, s in enumerate(manifest):
        parts = []
        if "title" in s:
            text, loc = s["title"]
            parts.append(f'<h1 class="gravia-title" style="{get_style(loc)}">{text}</h1>')
        if "subtitle" in s:
            text, loc = s["subtitle"]
            parts.append(f'<div class="gravia-element" style="{get_style(loc)}">{text}</div>')
        if "body" in s:
            bodies = s["body"] if isinstance(s["body"], list) else [s["body"]]
            for text, loc in bodies:
                parts.append(f'<div class="gravia-element" style="{get_style(loc)}">{text}</div>')
        if "figure" in s:
            src, loc = s["figure"]
            parts.append(f'<iframe src="{src}" style="{get_iframe_style(loc)}"></iframe>')
            
        slides_html += f'            <section data-transition="fade">\n'
        slides_html += "\n".join([f"                {p}" for p in parts])
        slides_html += f'\n            </section>\n'

    # Read template and manually replace
    template_path = Path("gravia/slidetheater/templates/madelane.html.j2")
    if template_path.exists():
        template_content = template_path.read_text()
    else:
        # Fallback to a basic Reveal.js structure if template is missing
        template_content = """<!doctype html><html><head><meta charset="utf-8">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.css">
        <style>{{ extra_css }}</style></head>
        <body><div class="reveal"><div class="slides">{{ slides_html }}</div></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/4.3.1/reveal.min.js"></script>
        <script>Reveal.initialize({hash: true, center: true, transition: 'fade'});</script></body></html>"""

    # Basic string replacement (simulating Jinja2)
    html = template_content
    html = html.replace('{{ deck_title | default("Gravia Presentation") }}', "Omission Mismatch Prediction Error")
    html = html.replace('{{ reveal_version }}', "4.3.1")
    html = html.replace('{% if extra_css %}', "").replace('{% endif %}', "")
    html = html.replace('{{ extra_css }}', extra_css)
    html = html.replace('{% if plotly_js %}', "").replace('{% endif %}', "")
    html = html.replace('{{ footer_text | default("Gravia | Research Factory") }}', "Hamed Nejat | BastosLab | Vanderbilt University")
    html = html.replace('<div class="gravia-global-footer">BASTOS LAB | VANDERBILT UNIVERSITY | 2024</div>', '<div class="gravia-global-footer">BASTOS LAB | VANDERBILT UNIVERSITY | 2024</div>')
    
    # Handle the slides loop
    start_tag = '{% for slide in slides %}'
    end_tag = '{% endfor %}'
    start_idx = html.find(start_tag)
    end_idx = html.find(end_tag) + len(end_tag)
    if start_idx != -1 and end_idx != -1:
        html = html[:start_idx] + slides_html + html[end_idx:]

    # Final cleanup of remaining Jinja tags
    import re
    html = re.sub(r'{{.*?}}', '', html)
    html = re.sub(r'{%.*?%}', '', html)

    output_path = Path("presentation.html")
    output_path.write_text(html)
    print(f"✅ Presentation generated: {output_path}")

if __name__ == "__main__":
    generate_presentation()
