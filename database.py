from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:postgres@db:5432/contactsdb"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
