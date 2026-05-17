from tests.conftest import TestingSessionLocal
from app.models.user import User


def test_user_table_created():
    db = TestingSessionLocal()
    user = User(email="seller@shopfix.test", hashed_password="x", display_name="Ada")
    db.add(user)
    db.commit()
    assert db.query(User).filter_by(email="seller@shopfix.test").one().display_name == "Ada"
    db.close()
