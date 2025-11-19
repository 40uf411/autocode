import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

BLUEPRINT_DIR = Path(__file__).resolve().parent.parent / "blueprint"
OUTPUTS = {
    "model": ("app/infrastructure/db", "custom_{name}_model.py", "model.py.tpl"),
    "schema": ("app/api", "custom_{name}_schemas.py", "schema.py.tpl"),
    "repository": ("app/infrastructure/db", "custom_{name}_repository.py", "repository.py.tpl"),
    "service": ("app/services", "custom_{name}_service.py", "service.py.tpl"),
    "router": ("app/api/routes", "custom_{name}.py", "router.py.tpl"),
}
PRIMITIVES = {
    "int": ("Integer", "int"),
    "string": ("String(255)", "str"),
    "text": ("Text", "str"),
    "bool": ("Boolean", "bool"),
    "datetime": ("DateTime(timezone=True)", "datetime | None"),
    "float": ("Float", "float"),
}


def snake_case(name: str) -> str:
    result = ""
    for char in name:
        if char.isupper():
            if result:
                result += "_"
            result += char.lower()
        else:
            result += char
    return result


def render_template(template: str, context: Dict[str, str]) -> str:
    for key, value in context.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template


def load_entities(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of entities")
    return data


def purge_existing_files() -> None:
    folders = [
        "app/infrastructure/db",
        "app/api",
        "app/api/routes",
        "app/services",
    ]
    for folder in folders:
        for file in Path(folder).glob("custom_*.py"):
            file.unlink()


def build_model_context(entity: dict) -> Dict[str, str]:
    entity_name = entity["name"]
    class_name = entity_name
    snake = snake_case(entity_name)
    table_name = entity.get("table", f"{snake}s")
    attrs = entity.get("attributes", [])
    imports = {
        "from app.infrastructure.db.base import Base",
        "from sqlalchemy.orm import Mapped, mapped_column",
    }
    field_lines = []
    for attr in attrs:
        a_type = attr.get("type", "string")
        name = attr["name"]
        nullable = attr.get("nullable", True)
        primary_key = attr.get("primary_key", False)
        default = attr.get("default")

        if a_type == "reference":
            target = attr["target"]
            imports.add("from sqlalchemy import ForeignKey")
            python_type = attr.get("python_type", "int | None")
            line = f"    {name}: Mapped[{python_type}] = mapped_column(ForeignKey('{target}'), nullable={nullable})"
        elif a_type == "list":
            target = attr["target"]
            back_populates = attr.get("back_populates")
            imports.add("from sqlalchemy.orm import relationship")
            line = f'    {name}: Mapped[list["{target}"]] = relationship("{target}"'
            if back_populates:
                line += f', back_populates="{back_populates}"'
            line += ")"
        else:
            sql_type, py_type = PRIMITIVES.get(a_type, PRIMITIVES["string"])
            if a_type == "string" and attr.get("length"):
                sql_type = f"String({attr['length']})"
            params = []
            if primary_key:
                params.append("primary_key=True")
            if not nullable:
                params.append("nullable=False")
            if default is not None:
                params.append(f"default={default!r}")
            param_str = ", " + ", ".join(params) if params else ""
            line = f"    {name}: Mapped[{py_type}] = mapped_column({sql_type}{param_str})"
        field_lines.append(line)
    import_block = "\n".join(sorted(imports))
    fields = "\n".join(field_lines) if field_lines else "    pass"
    return {
        "IMPORTS": import_block,
        "CLASS_NAME": class_name,
        "TABLE_NAME": table_name,
        "FIELDS": fields,
    }


def build_schema_context(entity: dict) -> Dict[str, str]:
    attrs = entity.get("attributes", [])
    lines = []
    for attr in attrs:
        if attr.get("type") in {"list", "reference"}:
            continue
        _, py_type = PRIMITIVES.get(attr.get("type"), PRIMITIVES["string"])
        default = " = None" if attr.get("nullable", True) else ""
        lines.append(f"    {attr['name']}: {py_type}{default}")
    if not lines:
        lines = ["    pass"]
    return {
        "CLASS_NAME": entity["name"],
        "SCHEMA_FIELDS": "\n".join(lines),
    }


def build_repository_context(entity: dict) -> Dict[str, str]:
    return {
        "CLASS_NAME": entity["name"],
        "ORM_IMPORT": f"{entity['name']}ORM",
    }


def build_service_context(entity: dict) -> Dict[str, str]:
    snake = snake_case(entity["name"])
    repository_path = f"app.infrastructure.db.custom_{snake}_repository"
    return {
        "CLASS_NAME": entity["name"],
        "REPOSITORY_IMPORT": repository_path,
    }


def build_router_context(entity: dict) -> Dict[str, str]:
    snake = snake_case(entity["name"])
    service_path = f"app.services.custom_{snake}_service"
    schema_path = f"app.api.custom_{snake}_schemas"
    return {
        "CLASS_NAME": entity["name"],
        "ROUTE_NAME": snake,
        "SERVICE_IMPORT": service_path,
        "SCHEMA_IMPORT": schema_path,
    }


CONTEXT_BUILDERS = {
    "model": build_model_context,
    "schema": build_schema_context,
    "repository": build_repository_context,
    "service": build_service_context,
    "router": build_router_context,
}


def generate_entity(entity: dict) -> None:
    snake = snake_case(entity["name"])
    for key, (directory, filename_template, template_name) in OUTPUTS.items():
        template_path = BLUEPRINT_DIR / template_name
        template = template_path.read_text(encoding="utf-8")
        builder = CONTEXT_BUILDERS[key]
        context = builder(entity)
        context.setdefault("CLASS_NAME", entity["name"])
        context.setdefault("TABLE_NAME", f"{snake}s")
        rendered = render_template(template, context)
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / filename_template.format(name=snake)
        output_file.write_text(rendered.rstrip() + "\n", encoding="utf-8")
        print(f"Wrote {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate custom entity scaffolding.")
    parser.add_argument(
        "--config",
        default="entities.json",
        help="Path to the JSON file describing entities (default: entities.json).",
    )
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"Configuration file {config_path} not found.")
    purge_existing_files()
    entities = load_entities(config_path)
    for entity in entities:
        generate_entity(entity)


if __name__ == "__main__":
    main()
