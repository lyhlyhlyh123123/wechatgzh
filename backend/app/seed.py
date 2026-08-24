from sqlalchemy.orm import Session

from app.models import Topic

SEED_TOPICS = [
    ("欲望", "情感关系", "越成熟的女人越有魅力，是被生活打磨出来的"),
    ("比较", "年龄变化", "同龄人都结婚生子了，我还在等什么"),
    ("恐惧", "情感关系", "如果一直遇不到合适的人，该怎么办"),
    ("窥私", "婚姻", "一个40岁的女人离婚后，过得好吗"),
    ("站队", "婚姻", "婚姻应该选择爱情，还是稳定"),
    ("比较", "女性成长", "月薪五万以后，为什么还是不快乐"),
    ("恐惧", "年龄变化", "35岁以后，是不是就没有资格挑了"),
    ("欲望", "两性关系", "被选择和主动选择，哪个更让人安心"),
    ("窥私", "成年人的现实", "那些嫁得好的女生，后来都怎么样了"),
    ("站队", "情感关系", "心动和稳定，只能选一个"),
    ("比较", "人生阶段", "38岁还单身，真的比结婚晚了吗"),
    ("恐惧", "成年人的现实", "存款和安全感，到底哪个先来"),
]


def ensure_seed(session: Session) -> None:
    existing = {c for (c,) in session.query(Topic.conflict).all()}
    added = False
    for drive_type, category, conflict in SEED_TOPICS:
        if conflict in existing:
            continue
        session.add(Topic(drive_type=drive_type, category=category, conflict=conflict))
        existing.add(conflict)
        added = True
    if added:
        session.commit()
