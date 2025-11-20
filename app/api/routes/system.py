from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from app.api.dependencies import require_superuser
from app.infrastructure.db.base import Base

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/ping")
async def ping() -> dict[str, str | int]:
    now = datetime.now(timezone.utc)
    return {"unix": int(now.timestamp()), "iso": now.isoformat()}


@router.get("/editable-resources")
async def editable_resources() -> dict[str, List[str]]:
    tables: List[str] = []
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__editable__", False):
            tables.append(cls.__tablename__)
    return {"resources": sorted(set(tables))}


def _format_default(default: Any) -> Optional[str]:
    if default is None:
        return None
    arg = getattr(default, "arg", default)
    if callable(arg):
        return getattr(arg, "__name__", repr(arg))
    try:
        return str(arg)
    except Exception:  # pragma: no cover - fallback for exotic defaults
        return repr(arg)


def _describe_column(column: Any) -> Dict[str, Any]:
    foreign_keys = []
    for fk in column.foreign_keys:
        target = getattr(fk.column, "table", None)
        if target is not None:
            foreign_keys.append(f"{target.name}.{fk.column.name}")
    return {
        "name": column.name,
        "type": str(column.type),
        "nullable": column.nullable,
        "primary_key": column.primary_key,
        "unique": bool(getattr(column, "unique", False)),
        "autoincrement": column.autoincrement is True,
        "default": _format_default(column.default),
        "server_default": _format_default(column.server_default),
        "foreign_keys": foreign_keys,
    }


def _describe_indexes(table: Any) -> List[Dict[str, Any]]:
    indexes: List[Dict[str, Any]] = []
    for index in sorted(table.indexes, key=lambda idx: idx.name or ""):
        indexes.append(
            {
                "name": index.name,
                "unique": bool(index.unique),
                "columns": [col.name for col in index.columns],
            }
        )
    return indexes


def _describe_table(table: Any) -> Dict[str, Any]:
    return {
        "name": table.name,
        "schema": table.schema,
        "columns": [_describe_column(column) for column in table.columns],
        "indexes": _describe_indexes(table),
    }


@router.get(
    "/schema",
    dependencies=[Depends(require_superuser)],
)
async def database_schema() -> Dict[str, Any]:
    tables = [_describe_table(table) for table in Base.metadata.sorted_tables]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "table_count": len(tables),
        "tables": tables,
    }


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
