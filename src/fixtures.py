"""Load seed data fixtures for development"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session
from passlib.context import CryptContext

from src.database import SessionLocal
from src.models import User, Paper, Tag, Embedding
from src.embeddings import generate_paper_embedding

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def load_fixtures(db: Session = None, fixtures_file: str = "fixtures/seed_data.json"):
    """
    Load seed data from JSON file.

    Args:
        db: Database session (optional, creates one if not provided)
        fixtures_file: Path to JSON fixtures file
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # Load fixtures
        fixtures_path = Path(fixtures_file)
        if not fixtures_path.exists():
            print(f"Error: Fixtures file not found at {fixtures_path}")
            return

        with open(fixtures_path, "r") as f:
            data = json.load(f)

        # Create users
        print("Creating users...")
        user_map = {}
        for user_data in data.get("users", []):
            # Check if user already exists
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()
            if existing_user:
                print(f"  User '{user_data['username']}' already exists, skipping...")
                user_map[user_data["username"]] = existing_user
                continue

            # Create new user
            password = user_data.pop("password")
            user = User(
                **user_data,
                password_hash=pwd_context.hash(password)
            )
            db.add(user)
            db.flush()  # Get the ID
            user_map[user_data["username"]] = user
            print(f"  Created user: {user.username}")

        db.commit()

        # Create papers and embeddings
        print("\nCreating papers and generating embeddings...")
        demo_user = user_map.get("demo")
        if not demo_user:
            print("Error: Demo user not found, cannot create papers")
            return

        for paper_data in data.get("papers", []):
            # Check if paper already exists
            existing_paper = db.query(Paper).filter(
                Paper.title == paper_data["title"],
                Paper.user_id == demo_user.id
            ).first()

            if existing_paper:
                print(f"  Paper '{paper_data['title'][:50]}...' already exists, skipping...")
                continue

            # Extract tags
            tag_names = paper_data.pop("tags", [])

            # Parse date_read
            date_read_str = paper_data.pop("date_read", None)
            date_read = None
            if date_read_str:
                date_read = datetime.strptime(date_read_str, "%Y-%m-%d").date()

            # Create paper
            paper = Paper(
                user_id=demo_user.id,
                date_read=date_read,
                **paper_data
            )
            db.add(paper)
            db.flush()  # Get the paper ID

            # Create/get tags and associate with paper
            for tag_name in tag_names:
                tag = db.query(Tag).filter(
                    Tag.name == tag_name,
                    Tag.user_id == demo_user.id
                ).first()

                if not tag:
                    tag = Tag(name=tag_name, user_id=demo_user.id)
                    db.add(tag)
                    db.flush()

                paper.tags.append(tag)

            # Generate and store embedding
            print(f"  Generating embedding for: {paper.title[:60]}...")
            try:
                embedding_vector = generate_paper_embedding(paper.abstract, paper.summary)
                embedding = Embedding(
                    paper_id=paper.id,
                    embedding_vector=embedding_vector.tolist(),  # pgvector accepts list
                    embedding_source="abstract_summary"
                )
                db.add(embedding)
            except Exception as e:
                print(f"    Warning: Failed to generate embedding: {e}")
                print(f"    Paper will be created without embedding")

            db.commit()
            print(f"  Created paper: {paper.title[:60]}...")

        print("\n✓ Fixtures loaded successfully!")
        print(f"  Users: {len(data.get('users', []))}")
        print(f"  Papers: {len(data.get('papers', []))}")
        print("\nYou can log in with:")
        print("  Username: demo")
        print("  Password: demo123")

    except Exception as e:
        print(f"Error loading fixtures: {e}")
        db.rollback()
        raise
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    """Run fixture loading from command line"""
    import sys

    print("Loading seed data fixtures...\n")

    # Check if custom fixtures file provided
    fixtures_file = "fixtures/seed_data.json"
    if len(sys.argv) > 1:
        fixtures_file = sys.argv[1]

    load_fixtures(fixtures_file=fixtures_file)
