"""make seed：重建 schema 并写入确定性种子数据（幂等）。"""

from app.database import SessionLocal, engine
from app.models import Base
from app.seeds.builder import seed_all


def main() -> None:
    print("⚠️  警告：即将删除并重建全部数据表（drop_all + create_all）")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    print("种子数据写入完成（锚点 2026-10-09）")


if __name__ == "__main__":
    main()
