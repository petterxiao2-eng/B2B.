"""
SQLite 增量迁移脚本（V2 真实化改造）。

设计原则：
- 禁止删库。仅做"新增表 + 新增列"，绝不 DROP。
- 可重复执行：已存在的表/列会被跳过。
- 新表通过 Base.metadata.create_all 创建（对已存在表无副作用）。
- 已有表的缺失列通过 ALTER TABLE ADD COLUMN 补齐（SQLite 仅支持加列）。

运行：python migrate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app.database import engine, Base
from app import models  # noqa: F401  确保模型已注册到 Base.metadata


def migrate():
    print(f"[migrate] database = {engine.url}")
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # 1) 创建尚不存在的表（company_sources / company_verifications / company_scores 等）
    Base.metadata.create_all(engine)
    for t in Base.metadata.tables:
        status = "已存在" if t in existing_tables else "已创建"
        print(f"  table {t}: {status}")

    # 2) 为已有表补齐缺失列（增量 ALTER）
    added = 0
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
        for col in table.columns:
            if col.name in existing_cols:
                continue
            # 编译列类型（按当前 dialect，SQLite 下 JSON->TEXT / Boolean->INTEGER 等）
            col_type = col.type.compile(dialect=engine.dialect)
            # SQLite ADD COLUMN 必须可空或带默认值；本系统新增列均为可空（Python 侧 default）
            sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}'
            with engine.begin() as conn:
                conn.execute(text(sql))
            print(f"  + {table_name}.{col.name} ({col_type})")
            added += 1

    print(f"[migrate] 完成。新增列 {added} 个，无数据丢失。")


if __name__ == "__main__":
    migrate()
