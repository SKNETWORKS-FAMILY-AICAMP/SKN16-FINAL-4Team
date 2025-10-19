from database import Base, engine
import models
from models import Base

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
