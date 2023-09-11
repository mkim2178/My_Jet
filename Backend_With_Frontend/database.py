import motor.motor_asyncio


# This is a motor client.
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017/")


# User database and collection.
user_db = client.User_DB
user_collection = user_db.user


# Ticket database and collection.
ticket_db = client.Ticket_DB
ticket_collection = ticket_db.ticket
