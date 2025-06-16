from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Contact
from schemas import ContactCreate, ContactUpdate

def create_contact(db: Session, contact: ContactCreate, current_user):
    db_contact = Contact(**contact.dict(), user_id=current_user.id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def get_contacts(db: Session, current_user, skip: int = 0, limit: int = 100):
    return (
        db.query(Contact)
        .filter(Contact.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_contact(db: Session, contact_id: int, current_user):
    return (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_id == current_user.id)
        .first()
    )

def update_contact(db: Session, contact_id: int, contact: ContactUpdate, current_user):
    db_contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_id == current_user.id)
        .first()
    )
    if db_contact:
        for key, value in contact.dict().items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact

def delete_contact(db: Session, contact_id: int, current_user):
    db_contact = (
        db.query(Contact)
        .filter(Contact.id == contact_id, Contact.user_id == current_user.id)
        .first()
    )
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact

def search_contacts(db: Session, query: str, current_user):
    return (
        db.query(Contact)
        .filter(
            (Contact.user_id == current_user.id) &
            (
                (Contact.first_name.ilike(f"%{query}%")) |
                (Contact.last_name.ilike(f"%{query}%")) |
                (Contact.email.ilike(f"%{query}%"))
            )
        )
        .all()
    )

def get_upcoming_birthdays(db: Session, current_user):
    today = date.today()
    in_7_days = today + timedelta(days=7)
    return (
        db.query(Contact)
        .filter(
            Contact.user_id == current_user.id,
            Contact.birthday >= today,
            Contact.birthday <= in_7_days
        )
        .all()
    )
