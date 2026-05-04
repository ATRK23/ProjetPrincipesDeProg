from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Restaurant, User
from app.security import (
    ALGORITHM,
    SECRET_KEY,
    ROLE_ADMIN,
    ROLE_RESTAURANT_OWNER,
    ROLE_USER,
    check_restaurant_owner_or_admin,
    check_user_is_self_or_admin,
    create_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_user_in_db(
    db_session,
    username="arthur",
    email="arthur@example.com",
    password="testpass123",
    role=ROLE_USER,
):
    user = User(
        username=username,
        email=email,
        role=role,
        hashed_password=hash_password(password),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_restaurant_in_db(db_session, owner_id=None):
    restaurant = Restaurant(
        name="Le Bon Plat",
        address="12 rue de Paris",
        phone="0102030405",
        description="Cuisine maison",
        is_open=True,
        owner_id=owner_id,
    )
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    return restaurant


def encode_token(payload):
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_hash_password_does_not_store_plain_text_and_verifies_password():
    password = "testpass123"

    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("wrong-password", hashed_password) is False


def test_hash_password_generates_different_hashes_for_same_password():
    password = "testpass123"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True


def test_create_access_token_keeps_subject_and_adds_expiration():
    token = create_access_token({"sub": "arthur@example.com"})

    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    assert decoded["sub"] == "arthur@example.com"
    assert "exp" in decoded


def test_get_current_user_returns_user_from_valid_token(db_session):
    user = create_user_in_db(db_session)
    token = create_access_token({"sub": user.email})

    current_user = get_current_user(token=token, db=db_session)

    assert current_user.id == user.id
    assert current_user.email == user.email


def test_get_current_user_rejects_malformed_token(db_session):
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token="not-a-jwt", db=db_session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token invalide"


def test_get_current_user_rejects_token_without_subject(db_session):
    token = encode_token(
        {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token invalide"


def test_get_current_user_rejects_expired_token(db_session):
    user = create_user_in_db(db_session)
    token = encode_token(
        {
            "sub": user.email,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token invalide"


def test_get_current_user_returns_404_when_user_no_longer_exists(db_session):
    token = create_access_token({"sub": "missing@example.com"})

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token, db=db_session)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Utilisateur introuvable"


def test_require_roles_allows_user_with_allowed_role():
    admin = User(
        id=1,
        username="admin",
        email="admin@example.com",
        role=ROLE_ADMIN,
        hashed_password="hashed",
    )
    checker = require_roles(ROLE_ADMIN)

    returned_user = checker(current_user=admin)

    assert returned_user is admin


def test_require_roles_rejects_user_with_forbidden_role():
    user = User(
        id=1,
        username="arthur",
        email="arthur@example.com",
        role=ROLE_USER,
        hashed_password="hashed",
    )
    checker = require_roles(ROLE_ADMIN)

    with pytest.raises(HTTPException) as exc_info:
        checker(current_user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Accès interdit"


def test_check_user_is_self_or_admin_allows_self():
    user = User(
        id=10,
        username="arthur",
        email="arthur@example.com",
        role=ROLE_USER,
        hashed_password="hashed",
    )

    assert check_user_is_self_or_admin(10, user) is None


def test_check_user_is_self_or_admin_allows_admin():
    admin = User(
        id=1,
        username="admin",
        email="admin@example.com",
        role=ROLE_ADMIN,
        hashed_password="hashed",
    )

    assert check_user_is_self_or_admin(10, admin) is None


def test_check_user_is_self_or_admin_rejects_other_user():
    user = User(
        id=1,
        username="arthur",
        email="arthur@example.com",
        role=ROLE_USER,
        hashed_password="hashed",
    )

    with pytest.raises(HTTPException) as exc_info:
        check_user_is_self_or_admin(2, user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Accès interdit"


def test_check_restaurant_owner_or_admin_allows_owner(db_session):
    owner = create_user_in_db(
        db_session,
        role=ROLE_RESTAURANT_OWNER,
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)

    assert check_restaurant_owner_or_admin(restaurant, owner) is None


def test_check_restaurant_owner_or_admin_allows_admin(db_session):
    owner = create_user_in_db(db_session)
    admin = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role=ROLE_ADMIN,
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)

    assert check_restaurant_owner_or_admin(restaurant, admin) is None


def test_check_restaurant_owner_or_admin_rejects_non_owner(db_session):
    owner = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    other_user = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)

    with pytest.raises(HTTPException) as exc_info:
        check_restaurant_owner_or_admin(restaurant, other_user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Accès interdit"
