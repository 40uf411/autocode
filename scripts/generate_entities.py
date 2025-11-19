import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

BLUEPRINT_DIR = Path(__file__).resolve().parent.parent / "blueprint"
OUTPUTS = {
    "model": ("app/infrastructure/db", "business_{name}_model.py", "model.py.tpl"),
    "schema": ("app/api", "business_{name}_schemas.py", "schema.py.tpl"),
    "repository": ("app/infrastructure/db", "business_{name}_repository.py", "repository.py.tpl"),
    "service": ("app/services", "business_{name}_service.py", "service.py.tpl"),
    "router": ("app/api/routes", "business_{name}.py", "router.py.tpl"),
}
PRIMITIVES = {
    "int": {"column": "Integer", "python": "int", "import": "Integer"},
    "string": {"column": "String(255)", "python": "str", "import": "String"},
    "text": {"column": "Text", "python": "str", "import": "Text"},
    "bool": {"column": "Boolean", "python": "bool", "import": "Boolean"},
    "datetime": {
        "column": "DateTime(timezone=True)",
        "python": "datetime | None",
        "import": "DateTime",
    },
    "float": {"column": "Float", "python": "float", "import": "Float"},
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
        for file in Path(folder).glob("business_*.py"):
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
    sqlalchemy_imports: set[str] = set()
    needs_datetime = False
    field_lines = []
    for attr in attrs:
        a_type = attr.get("type", "string")
        name = attr["name"]
        nullable = attr.get("nullable", True)
        primary_key = attr.get("primary_key", False)
        default = attr.get("default")

        if a_type == "reference":
            target = attr["target"]
            sqlalchemy_imports.add("ForeignKey")
            python_type = attr.get("python_type")
            if not python_type:
                python_type = "int" if not nullable else "int | None"
            line = f"    {name}: Mapped[{python_type}] = mapped_column(ForeignKey('{target}'), nullable={nullable})"
        elif a_type == "list":
            target = attr["target"]
            target_class = target if target.endswith("ORM") else f"{target}ORM"
            back_populates = attr.get("back_populates")
            imports.add("from sqlalchemy.orm import relationship")
            line = f'    {name}: Mapped[list["{target_class}"]] = relationship("{target_class}"'
            if back_populates:
                line += f', back_populates="{back_populates}"'
            line += ")"
        elif a_type == "relationship":
            target = attr["target"]
            target_class = target if target.endswith("ORM") else f"{target}ORM"
            back_populates = attr.get("back_populates")
            imports.add("from sqlalchemy.orm import relationship")
            nullable_relationship = attr.get("nullable", True)
            type_hint = f"{target_class}"
            if nullable_relationship:
                type_hint += " | None"
            line = f'    {name}: Mapped["{type_hint}"] = relationship("{target_class}"'
            if back_populates:
                line += f', back_populates="{back_populates}"'
            if (uselist := attr.get("uselist")) is not None:
                line += f", uselist={uselist}"
            line += ")"
        else:
            primitive = PRIMITIVES.get(a_type, PRIMITIVES["string"])
            sql_type = primitive["column"]
            py_type = primitive["python"]
            base_import = primitive["import"]
            if a_type == "string" and attr.get("length"):
                sql_type = f"String({attr['length']})"
                sqlalchemy_imports.add("String")
            else:
                sqlalchemy_imports.add(base_import)
            if "datetime" in py_type:
                needs_datetime = True
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
    if sqlalchemy_imports:
        imports.add("from sqlalchemy import " + ", ".join(sorted(sqlalchemy_imports)))
    if needs_datetime:
        imports.add("from datetime import datetime")
    # Ensure imports are consistently ordered for determinism
    import_block = "\n".join(sorted(imports))
    fields = "\n".join(field_lines) if field_lines else "    pass"
    return {
        "IMPORTS": import_block,
        "CLASS_NAME": f"{class_name}ORM",
        "TABLE_NAME": table_name,
        "FIELDS": fields,
    }


def build_schema_context(entity: dict) -> Dict[str, str]:
    attrs = entity.get("attributes", [])
    lines = []
    for attr in attrs:
        if attr.get("type") in {"list", "reference", "relationship"}:
            continue
        py_type = PRIMITIVES.get(attr.get("type"), PRIMITIVES["string"])["python"]
        default = " = None" if attr.get("nullable", True) else ""
        lines.append(f"    {attr['name']}: {py_type}{default}")
    if not lines:
        lines = ["    pass"]
    return {
        "CLASS_NAME": entity["name"],
        "SCHEMA_FIELDS": "\n".join(lines),
    }


def build_repository_context(entity: dict) -> Dict[str, str]:
    snake = snake_case(entity["name"])
    return {
        "CLASS_NAME": entity["name"],
        "ORM_CLASS": f"{entity['name']}ORM",
        "MODEL_MODULE": f"app.infrastructure.db.business_{snake}_model",
    }


def build_service_context(entity: dict) -> Dict[str, str]:
    snake = snake_case(entity["name"])
    repository_path = f"app.infrastructure.db.business_{snake}_repository"
    return {
        "CLASS_NAME": entity["name"],
        "REPOSITORY_IMPORT": repository_path,
    }


def build_router_context(entity: dict) -> Dict[str, str]:
    snake = snake_case(entity["name"])
    service_path = f"app.services.business_{snake}_service"
    schema_path = f"app.api.business_{snake}_schemas"
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
    parser = argparse.ArgumentParser(description="Generate business entity scaffolding.")
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
