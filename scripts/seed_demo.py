"""Seed a demo user with driver shots for testing the frontend."""
from backend.app.database import SessionLocal, engine, Base
from backend.app.models import User, ClubSpec, SwingSession, Shot
from scripts.seed_clubs import seed_clubs_from_csv


def seed_demo():
    Base.metadata.create_all(engine)
    db = SessionLocal()

    # Check if demo user already exists
    existing = db.query(User).filter(User.email == "demo@swingfit.com").first()
    if existing:
        print(f"Demo user already exists (id={existing.id})")
        db.close()
        return

    # Create demo user
    user = User(email="demo@swingfit.com", username="demo", hashed_password="demo")
    db.add(user)
    db.commit()

    # Seed clubs
    count = seed_clubs_from_csv(db, "data/club_specs/initial_seed.csv")
    print(f"Seeded {count} clubs")

    # Create a session with 15 driver shots
    session = SwingSession(
        user_id=user.id,
        launch_monitor_type="trackman_4",
        data_source="file_upload",
    )
    db.add(session)
    db.commit()

    import random
    random.seed(42)
    for i in range(15):
        db.add(Shot(
            session_id=session.id,
            club_used="driver",
            ball_speed=148.0 + random.gauss(0, 2),
            launch_angle=13.5 + random.gauss(0, 0.8),
            spin_rate=3000.0 + random.gauss(0, 200),
            carry_distance=247.0 + random.gauss(0, 5),
            total_distance=270.0 + random.gauss(0, 6),
            club_speed=104.5 + random.gauss(0, 1.5),
            attack_angle=-1.0 + random.gauss(0, 0.5),
            face_to_path=-1.2 + random.gauss(0, 0.8),
            offline_distance=5.0 + random.gauss(0, 6),
            smash_factor=1.41 + random.gauss(0, 0.01),
            shot_number=i + 1,
        ))

    db.commit()
    print(f"Created demo user (id={user.id}) with 15 driver shots")
    db.close()


if __name__ == "__main__":
    seed_demo()
