from auth import get_hashed_password
from models import TicketInDB, UserInDB
from database import user_collection, ticket_collection


async def is_duplicate_login_id(user_login_id):
    """
    Logic:
    1. Calls 'find_one' pymongo function by using 'user_login_id' as a condition.
    2. If it returns something, return False. Otherwise, return True.
    """

    duplicate = await user_collection.find_one({"login_id": user_login_id})
    if not duplicate:
        return False
    return True



async def is_duplicate_email(user_email):
    """
    Logic:
    1. Calls 'find_one' pymongo function by using 'user_email' as a condition.
    2. If it returns something, return False. Otherwise, return True.
    """

    duplicate = await user_collection.find_one({"email": user_email})
    if not duplicate:
        return False
    return True


async def create_user(new_user):
    """
    Logic:
    1. First, it calls two functions: 'is_duplicate_login_id' and 'is_duplicate_email' to check if new user's 'login_id' or 'email' already exists on our database.
    2. If new user's 'login_id' already exists, return a string 'duplicate login_id'. If new user's 'email' alreay exists, return a string 'duplicate email'.
       - If both are valid, calls 'get_hashed_password' function to hash new user's pure password and go to step 3.
    3. Create a UserInDB object and convert UserCreate object into UserInDB.
       - The 'model_dump' function is super important. It converts the model object into the dictionary, and we need this process to insert our UserInDB object into the database.
       - The database requires dictionary format to store the data.
       - We can also use .dict() instead .model_dump() but it's not preferred.
    4. Then, use 'insert_one' pymongo function to insert the data.
    5. Finally, it returns a string that shows user's data is successfully stored in the database (this is for the debugging purpose).
    """

    duplicate_login_id = await is_duplicate_login_id(new_user.login_id)
    duplicate_email = await is_duplicate_email(new_user.email)
    if duplicate_login_id:
        return "duplicate login_id"
    if duplicate_email:
        return "duplicate email"
    hashed_password = get_hashed_password(new_user.password)
    store_user = UserInDB(
        login_id=new_user.login_id,
        email=new_user.email,
        birth_date=new_user.birth_date,
        sex=new_user.sex,
        full_name=new_user.full_name,
        hashed_password=hashed_password
        ).model_dump()
    user_collection.insert_one(store_user)
    return f"Welcome {new_user.full_name}. Your login id is <{new_user.login_id}>. Please login again."


async def delete_user(user):
    """
    Logic:
    1. Calls 'delete_one' pymongo function to delete user's data by user's login id.
    2. Returns a string for debugging purpose.
    """

    await user_collection.delete_one({"login_id": user["login_id"]})
    return f'Your account with login id: <{user["login_id"]}> has been deleted!'


async def ticket_is_valid(ticket):  # User cannot book two flights per day. The 'starting_point' and 'ending_point' should be different.
    """
    This function will check the following policies.
        1. User cannot book two flights per day.
        2. The 'starting_point' and 'ending_point' should be different.

    Logic:
    1. First, it will check the 'starting_point' and 'ending_point' are same. If they are same, it will immediately return False.
    2. Otherwise, it will use 'find' and 'to_list(None)' functions to store every TicketInDB object in a list.
    3. It will iterate the entire list and if one of the tickets from the list has the same departure date and owner login id as the parameter 'ticket' returns False.
    4. Otherwise, return True, which means the ticket contains valid information.
    """

    if ticket['starting_point'] == ticket['ending_point']:
        return False
    every_ticket = await ticket_collection.find({}).to_list(None)
    for t in every_ticket:
        if t['departure_date'] == ticket['departure_date'] and t['owner_login_id'] == ticket['owner_login_id']:
            return False
    return True


async def update_user_mileage(user):
    """
    Users will earn 100 mileages per ticket. It uses a '$inc' operator that increase a specific value.
    Returns a string for debugging.
    """

    user_collection.update_one({"login_id": user["login_id"]}, {"$inc": {"mileage": 100}})
    return f"You got 100 mileages!"


async def create_ticket(user, new_ticket):
    """
    Logic:
    1. First, it uses the 'model_dump' function to convert the 'new_ticket' (this is a 'TicketCreate' object) object into a dictionary.
    2. Then, it will use a double asterisk -> ** to unwrap the dictionary and use the values for 'TicketInDB' object's parameter.
       (ex) user_dict = new_ticket.model_dump() = {'starting_point': 'some string', 'ending_point': 'some string', 'departure_date': 'some string', 'jet_type': 'some string'}
            TicketInDB(**new_ticket.model_dump(), owner_login_id=user["login_id"]) = TicketInDB(starting_point=user_dict['starting_point'],
                                                                                                ending_point=user_dict['ending_point'],
                                                                                                departure_date=user_dict['departure_date'],
                                                                                                jet_type=user_dict['jet_type'],
                                                                                                owner_login_id=user["login_id"])
    3. The 'owner_login_id' class attribute from 'TicketInDB' object should be passed in from user["login_id"] because the parameter 'user' is already a dictionary.
    4. After steps 2 and 3, it will call the 'ticket_is_valid' function to check if user is booking another flight on a same day that user already booked before
       - Or if user's input of 'starting_point' and 'ending_point' are same.
    5. If it gives False, return None.
    6. Otherwise, call the 'insert_one' pymongo function to add the 'TicketInDB' object into the ticket database.
    7. Then, call 'update_user_mileage' function to increase the mileage (it will give 100 mileages to the user after he/she book a flight).
    8. Finally, it returns a string (it's a check message for debugging purpose).
    """

    store_ticket = TicketInDB(**new_ticket.model_dump(), owner_login_id=user["login_id"]).model_dump()
    is_valid = await ticket_is_valid(store_ticket)
    if not is_valid:
        return None
    await ticket_collection.insert_one(store_ticket)
    received_mileage = await update_user_mileage(user)
    return f"new ticket has added!" + received_mileage



async def read_every_ticket(user):
    """
    This function simply reads every ticket that contains user's 'login_id' as an 'owner_login_id.'

    Logic:
    1. First, it will use the 'find' and 'to_list(None)' pymongo functions to get every TicketInDB objects from the ticket database.
    2. Then, it will initialize an 'index' (int) variable and 'ticket_dict' (empty dictionary) variable to return.
    3. The 'result' is a list of 'TicketInDB' object, and it will use for loop to iterate every object in 'result' list.
    4. While iterating, it will use 'pop' python built-in function to get rid of a specific key called '_id'.
    5. After that, it will initialize a new 'key' variable which is a string 'Ticket ' with its number (it will cast our 'index' variable to make it string).
    6. Next, it will define a new key and value in the 'ticket_dict' dictionary -> ex) {"Ticket 1" : TicketInDB object}
    7. Finally, it will return the 'ticket_dict' dictionary.
    """

    tickets = await ticket_collection.find({"owner_login_id": user["login_id"]}).to_list(None)
    index = 1
    ticket_dict = {}
    for ticket in tickets:
        ticket.pop('_id')
        key = 'Ticket ' + str(index)
        index += 1
        ticket_dict[key] = ticket
    return ticket_dict


async def cancel_every_ticket(user):
    """
    Logic:
    1. Calls 'delete_many' pymongo function to delete every ticket that contains the "owner_login_id" as current user's 'login_id.'
    2. Then, it calls the 'update_one' pymongo function to set the current user's mileage to 0.
       - If user cancels every flight, the mileage should be 0 (It is a refund so the mileage that user received will not count anymore).
    3. Returns a string (for a debugging purpose).
    """

    await ticket_collection.delete_many({"owner_login_id": user["login_id"]})
    await user_collection.update_one({"login_id": user["login_id"]}, {"$set": {"mileage": 0}})
    return f"Your tickets are all deleted."



async def cancel_ticket_by_departure_date(cancel_date, user):
    """
    Logic:
    1. First, it uses a 'find_one' pymongo function by inputting a 'cancel_date' as a condition.
       - It will return None if there is no ticket that contains the 'cancel_date' as the 'departure_date.'
    2. After step 1, it will call the 'delete_one' pymongo function to delete a specific TicketInDB object from the ticket object.
       - It will check two conditions: 1) The 'departure_date' and 'cancel_date' should be same.
                                       2) The 'owner_login_id' should be same as the user's 'login_id.'
    3. Then, it will use the 'update_one' pymongo function to update the mileage.
       - It will use the '$inc' operator with a negative number to take off 100 mileages from user's total mileage.
    4. Returns a string (for debugging purpose).
    """

    check_ticket = await ticket_collection.find_one({"departure_date": cancel_date})
    if check_ticket is None:
        return None
    await ticket_collection.delete_one({"departure_date": cancel_date, "owner_login_id": user["login_id"]})
    await user_collection.update_one({"login_id": user["login_id"]}, {"$inc": {"mileage": -100}})
    return f"Your flight on {cancel_date} has been deleted."


# These functions will be used in the future (updating user's OR ticket's information) [maybe???]. Some of them are created for debugging purpose.
# async def update_jet_type(user, update_request):
#     """
#     updates a certain ticket's 'jet_type.'
#     """
#
#     await ticket_collection.update_one({"$and": [{"owner_login_id": user["login_id"], "departure_date": update_request.departure_date}]}, {"$set": {"jet_type": update_request.new_jet_type}})
#     return f"your jet type has updated (flight date {update_request.departure_date})"
#
#
# async def update_user_email(user, update_request):
#     """
#     updates user's email.
#     """
#
#     await user_collection.update_one({"email": user["email"]}, {"$set": {"email": update_request.new_email}})
#     return "your email has updated"
#
#
# async def delete_user_with_id(id):
#     """
#     This function has been created for debugging purpose.
#     Same logic as delete_user but the 'id' parameter is user's login_id.
#     """
#
#     await user_collection.delete_one({"login_id": id})
#     return f"user with login_id: {id} has been deleted!"
