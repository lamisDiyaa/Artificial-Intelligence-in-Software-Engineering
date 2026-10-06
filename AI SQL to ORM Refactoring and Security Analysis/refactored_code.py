import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import String, create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


# ============================================================
# 1. Database Configuration
# ============================================================

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "example_db")

if not DB_USER or not DB_PASSWORD:
    raise RuntimeError(
        "Database credentials are not configured. "
        "Set DB_USER and DB_PASSWORD environment variables."
    )

DATABASE_URL = (
    f"mysql+mysqlconnector://"
    f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


# ============================================================
# 2. SQLAlchemy Engine
# ============================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)


# ============================================================
# 3. Declarative Base
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# 4. User ORM Model
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"User("
            f"id={self.id!r}, "
            f"username={self.username!r}, "
            f"email={self.email!r}"
            f")"
        )


# ============================================================
# 5. Create Database Tables
# ============================================================

def create_tables() -> None:
    """Create all tables defined by the SQLAlchemy models."""
    Base.metadata.create_all(engine)


# ============================================================
# 6. Session Context Manager
# ============================================================

@contextmanager
def get_session() -> Iterator[Session]:
    """
    Provide a SQLAlchemy Session with automatic rollback
    on errors and proper cleanup.
    """
    session = Session(engine)

    try:
        yield session
        session.commit()

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


# ============================================================
# 7. Create User
# ============================================================

def create_user(username: str, email: str) -> User | None:
    """Create and persist a new user."""

    username = username.strip()
    email = email.strip().lower()

    if not username or not email:
        raise ValueError("Username and email are required.")

    if len(username) > 50:
        raise ValueError("Username must not exceed 50 characters.")

    if len(email) > 255:
        raise ValueError("Email must not exceed 255 characters.")

    new_user = User(
        username=username,
        email=email,
    )

    try:
        with get_session() as session:
            session.add(new_user)

            # Send the INSERT statement to the database
            # so the generated ID becomes available.
            session.flush()

            print(
                f"User '{new_user.username}' "
                f"created successfully with ID {new_user.id}."
            )

            return new_user

    except IntegrityError as exc:
        print(
            "Could not create user. "
            "Username or email may already exist."
        )
        print(f"Database error: {exc}")
        return None

    except SQLAlchemyError as exc:
        print(f"Database error while creating user: {exc}")
        return None


# ============================================================
# 8. Get User by Username
# ============================================================

def get_user_by_username(username: str) -> User | None:
    """Retrieve one user by username."""

    username = username.strip()

    with get_session() as session:
        statement = select(User).where(
            User.username == username
        )

        user = session.scalar(statement)

        return user


# ============================================================
# 9. Update User Email
# ============================================================

def update_user_email(
    username: str,
    new_email: str,
) -> bool:
    """Update the email address of an existing user."""

    username = username.strip()
    new_email = new_email.strip().lower()

    if not username or not new_email:
        raise ValueError(
            "Username and new email are required."
        )

    if len(new_email) > 255:
        raise ValueError(
            "Email must not exceed 255 characters."
        )

    try:
        with get_session() as session:
            statement = select(User).where(
                User.username == username
            )

            user = session.scalar(statement)

            if user is None:
                print(f"User '{username}' was not found.")
                return False

            user.email = new_email

            print(
                f"Email for user '{username}' "
                f"updated successfully."
            )

            return True

    except IntegrityError:
        print(
            "Could not update email. "
            "The email may already belong to another user."
        )
        return False

    except SQLAlchemyError as exc:
        print(
            f"Database error while updating user: {exc}"
        )
        return False


# ============================================================
# 10. Delete User
# ============================================================

def delete_user(username: str) -> bool:
    """Delete a user by username."""

    username = username.strip()

    try:
        with get_session() as session:
            statement = select(User).where(
                User.username == username
            )

            user = session.scalar(statement)

            if user is None:
                print(f"User '{username}' was not found.")
                return False

            session.delete(user)

            print(
                f"User '{username}' deleted successfully."
            )

            return True

    except SQLAlchemyError as exc:
        print(
            f"Database error while deleting user: {exc}"
        )
        return False


# ============================================================
# 11. List Users
# ============================================================

def list_users() -> list[User]:
    """Return all users ordered by ID."""

    with get_session() as session:
        statement = select(User).order_by(User.id)

        users = list(
            session.scalars(statement).all()
        )

        return users


# ============================================================
# 12. Main Program
# ============================================================

if __name__ == "__main__":

    # Create database tables if they do not already exist.
    create_tables()

    # --------------------------------------------------------
    # Create a new user
    # --------------------------------------------------------

    created_user = create_user(
        username="john_doe",
        email="john@example.com",
    )

    # --------------------------------------------------------
    # Get the newly created user by username
    # --------------------------------------------------------

    user = get_user_by_username("john_doe")

    if user:
        print(
            f"Found user: "
            f"{user.username} - {user.email}"
        )

    # --------------------------------------------------------
    # Update user's email
    # --------------------------------------------------------

    update_user_email(
        username="john_doe",
        new_email="john.new@example.com",
    )

    # --------------------------------------------------------
    # List all users
    # --------------------------------------------------------

    print("\nAll users:")

    for user in list_users():
        print(user)

    # --------------------------------------------------------
    # Delete user
    # --------------------------------------------------------

    # Uncomment the following line if you want to delete
    # the test user.

    # delete_user("john_doe")