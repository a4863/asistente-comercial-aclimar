from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_session_factory(url: str):
    return sessionmaker(bind=create_engine(url, future=True), expire_on_commit=False)
