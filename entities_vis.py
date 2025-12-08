#!/usr/bin/env python3
"""
Generate a clean HTML class diagram from entities.json using Mermaid.js.

- Each class shows attributes like: "id: uuid [PK] [NOT NULL]".
- Relations are edges with compact label boxes containing:
    * attribute name
    * relation type (ref / rel / list)
    * DB target (if available)
    * back=... (if back_populates)
    * ! (if nullable == False)
- Classes mentioned in relations but not defined in entities.json
  are added as empty placeholder classes (no attributes).

Usage:
    python entities_to_html.py entities.json --out class_diagram.html
"""

import argparse
import json
import re


# ---------- model building ----------

def infer_class_name_from_table(table_name: str) -> str:
    """Convert a table name into a class name, e.g. 'countries' -> 'Country'."""
    base = table_name.strip()
    if base.endswith("ies"):
        base = base[:-3] + "y"
    elif base.endswith("s"):
        base = base[:-1]
    return base[:1].upper() + base[1:]


def build_model(entities):
    """
    Build:
      - classes: dict[class_name] -> entity dict
      - edges: list of relationship dicts
    """
    classes = {}
    table_to_class = {}

    # First pass – copy entities and map table names
    for ent in entities:
        name = ent["name"]
        table = ent.get("table")

        ent_copy = json.loads(json.dumps(ent))  # deep copy
        ent_copy.setdefault("attributes", [])
        ent_copy["placeholder"] = False

        classes[name] = ent_copy
        if table:
            table_to_class[table] = name

    edges = []

    def ensure_placeholder(class_name: str):
        """Create an empty placeholder class node if not already defined."""
        if class_name not in classes:
            classes[class_name] = {
                "name": class_name,
                "table": None,
                "attributes": [],
                "placeholder": True,
            }

    # Second pass – resolve relationships/references and record edges
    for ent in list(classes.values()):
        src_class = ent["name"]

        for attr in ent.get("attributes", []):
            attr_type = attr.get("type")
            if attr_type not in ("reference", "relationship", "list"):
                continue

            target_spec = attr.get("target")
            if not target_spec:
                continue

            tgt_attr = None
            if attr_type == "reference" and "." in target_spec:
                # e.g. "countries.id"
                table_name, tgt_attr = target_spec.split(".", 1)
                tgt_class = table_to_class.get(table_name)
                if not tgt_class:
                    tgt_class = infer_class_name_from_table(table_name)
            else:
                # relationship / list: target is a class name
                tgt_class = target_spec

            ensure_placeholder(tgt_class)

            attr["target_class"] = tgt_class
            attr["target_attr"] = tgt_attr

            edges.append(
                {
                    "src": src_class,
                    "dst": tgt_class,
                    "attr_name": attr.get("name"),
                    "attr_type": attr_type,
                    "raw_target": target_spec,
                    "target_class": tgt_class,
                    "target_attr": tgt_attr,
                    "back_populates": attr.get("back_populates"),
                    "nullable": attr.get("nullable", True),
                }
            )

    return classes, edges


def format_attribute(attr) -> str:
    """
    Mermaid-safe attribute representation inside a class:
        "id: uuid [PK] [NOT NULL]"
        "country_id: reference"
    """
    name = attr.get("name", "")
    t = attr.get("type", "")
    flags = []
    if attr.get("primary_key"):
        flags.append("PK")
    if attr.get("nullable") is False:
        flags.append("NOT NULL")
    flag_str = ""
    if flags:
        flag_str = " " + " ".join(f"[{f}]" for f in flags)
    text = f"{name}: {t}{flag_str}".strip()
    return text


def clean_label(text: str) -> str:
    """
    Keep only characters that are safe in Mermaid labels
    (no angle brackets or brackets to avoid syntax conflicts).
    """
    return re.sub(r"[^0-9A-Za-z_.! =]", "_", text)


def build_edge_label(e) -> str:
    """
    Build a compact, single-line label for a relation.

    Pattern:
        attr_name type raw_target ! back=foo

    Examples:
        "country_id ref countries.id !"
        "owner rel Employee back=assigned_equipment"
        "assigned_equipment list Equipment"
    """
    parts = []

    if e["attr_name"]:
        parts.append(e["attr_name"])

    t = e["attr_type"] or ""
    t_short = {"reference": "ref", "relationship": "rel", "list": "list"}.get(t, t)
    if t_short:
        parts.append(t_short)

    if e["raw_target"]:
        parts.append(e["raw_target"])

    if e["nullable"] is False:
        parts.append("!")

    if e.get("back_populates"):
        parts.append("back=" + e["back_populates"])

    label = " ".join(parts) if parts else "rel"
    return clean_label(label)


def build_mermaid_code(classes, edges) -> str:
    """
    Convert classes + edges into Mermaid classDiagram DSL with
    nice defaults and left-to-right layout.
    """
    lines = []

    # Mermaid init – theme + some spacing tweaks
    init_block = (
        "%%{init: {"
        " 'theme': 'neutral',"
        " 'classDiagram': {"
        "   'diagramPadding': 30,"
        "   'minEntityWidth': 160,"
        "   'minEntityHeight': 70"
        " }"
        "}}%%"
    )
    lines.append(init_block)

    lines.append("classDiagram")
    lines.append("direction LR")  # left-to-right layout

    # Classes
    for class_name in sorted(classes.keys()):
        ent = classes[class_name]
        attrs = ent.get("attributes", [])

        if attrs:
            lines.append(f"    class {class_name} {{")
            for attr in attrs:
                text = format_attribute(attr)
                if text:
                    lines.append(f"        + {text}")
            lines.append("    }")
        else:
            # placeholder / no attributes
            lines.append(f"    class {class_name}")

    # Edges
    seen_edges = set()
    for e in edges:
        src = e["src"]
        dst = e["dst"]
        label = build_edge_label(e)

        if e["attr_type"] == "list":
            # 1-to-many style
            line = f'    {src} "1" --> "*" {dst} : {label}'
        else:
            line = f"    {src} --> {dst} : {label}"

        if line not in seen_edges:
            seen_edges.add(line)
            lines.append(line)

    return "\n".join(lines)


# ---------- HTML generation ----------

def build_html(mermaid_code: str, title: str = "Class Diagram") -> str:
    """
    Wrap Mermaid code into a nice standalone HTML document.

    Contains:
      - Mermaid.js for rendering
      - html2canvas for screenshots
      - Toolbar with "Download diagram as PNG"
      - Clean CSS including styling of class boxes and relation-label boxes
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f3f4f6;
    }}
    #toolbar {{
      padding: 0.5rem 1rem;
      background: #ffffff;
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    #diagram-frame {{
      margin: 1rem;
      padding: 1rem;
      background: #ffffff;
      border-radius: 10px;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
    }}
    #diagram-container {{
      overflow: auto;
    }}
    button {{
      padding: 0.4rem 0.9rem;
      border-radius: 6px;
      border: 1px solid #2563eb;
      background: #2563eb;
      color: #ffffff;
      cursor: pointer;
      font-size: 0.9rem;
    }}
    button:hover {{
      background: #1d4ed8;
    }}

    /* Mermaid class diagram styling */
    .mermaid .classGroup rect {{
      fill: #f5f3ff;
      stroke: #7c3aed;
      stroke-width: 1.2px;
      rx: 6;
      ry: 6;
    }}
    .mermaid .classTitle {{
      fill: #ede9fe;
      stroke: #7c3aed;
    }}
    .mermaid .classText {{
      fill: #111827;
      font-size: 11px;
    }}
    .mermaid .classLabel {{
      fill: #111827;
      font-weight: 600;
    }}
    .mermaid .edgeLabel text {{
      font-size: 10px;
      fill: #111827;
    }}
    /* Make relation labels look like small rounded boxes */
    .mermaid .edgeLabel > rect,
    .mermaid .edgeLabel > g > rect {{
      fill: #ffffff;
      stroke: #9ca3af;
      stroke-width: 1px;
      rx: 6;
      ry: 6;
    }}
  </style>

  <!-- Mermaid for diagram rendering -->
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <!-- html2canvas for screenshots -->
  <script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>

  <script>
    document.addEventListener('DOMContentLoaded', function () {{
      mermaid.initialize({{ startOnLoad: false, securityLevel: 'loose' }});
      mermaid.init(undefined, '.mermaid');

      document.getElementById('btn-screenshot').addEventListener('click', function () {{
        var frame = document.getElementById('diagram-frame');
        html2canvas(frame, {{
          backgroundColor: '#ffffff',
          scale: 2
        }}).then(function (canvas) {{
          var link = document.createElement('a');
          link.download = 'class_diagram.png';
          link.href = canvas.toDataURL('image/png');
          link.click();
        }});
      }});
    }});
  </script>
</head>
<body>
  <div id="toolbar">
    <button id="btn-screenshot">Download diagram as PNG</button>
  </div>

  <div id="diagram-frame">
    <div id="diagram-container" class="mermaid">
{mermaid_code}
    </div>
  </div>
</body>
</html>
"""


# ---------- CLI entrypoint ----------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a clean HTML UML-style class diagram from entities.json."
    )
    parser.add_argument("json_path", help="Path to entities.json")
    parser.add_argument(
        "--out",
        "-o",
        default="class_diagram.html",
        help="Output HTML file path (default: class_diagram.html)",
    )
    args = parser.parse_args()

    with open(args.json_path, "r", encoding="utf-8") as f:
        entities = json.load(f)

    classes, edges = build_model(entities)
    mermaid_code = build_mermaid_code(classes, edges)
    html = build_html(mermaid_code, title="Class Diagram")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)

    print("HTML diagram written to:", args.out)


if __name__ == "__main__":
    main()
