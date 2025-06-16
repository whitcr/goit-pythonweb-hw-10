from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship, DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Integer, default=0)   
    avatar = Column(String(255), nullable=True)

    contacts = relationship('Contact', back_populates='user')

class Contact(Base):
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=False, nullable=False)
    phone = Column(String(20), nullable=False)
    birthday = Column(Date, nullable=False)
    extra = Column(String(255))
    user_id = Column(Integer, ForeignKey('users.id'))   

    user = relationship('User', back_populates='contacts')
