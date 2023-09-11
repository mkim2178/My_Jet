from datetime import timedelta
from enum import Enum


from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import jwt, exceptions
from typing import Annotated


from auth import (get_current_user_by_token,
                  authenticate_user,
                  ACCESS_TOKEN_EXPIRE_MINUTES,
                  create_access_token,
                  SECRET_KEY,
                  ALGORITHM
                  )

from crud import (create_user,
                  create_ticket,
                  read_every_ticket,
                  delete_user,
                  cancel_every_ticket,
                  cancel_ticket_by_departure_date,
                  # update_user_email,
                  # update_jet_type,
                  # delete_user_with_id,
                  )

from models import (UserCreate,
                    UserInDB,
                    Token,
                    TicketCreate,
                    # EmailUpdateRequest,
                    # JetTypeUpdateRequest
                    )


app = FastAPI(
    title="My_Jet",
    contact={
        "name": "Minwoo Kim",
        "email": "mkim2178@berkeley.edu"
    }
)


# The program mount static files by using StaticFiles object. It also helps the program to use Jinja2Templates.
app.mount("/static", StaticFiles(directory="static"), name="static")


# Every HTMl file are stored in /templates directory
templates = Jinja2Templates(directory="templates")


# The Tags object inherits Enum, and it will be a tag for our REST API methods.
class Tags(Enum):
    for_user = "User Interactive"
    for_ticket = "Ticket Interactive"
    for_token = "Token Interactive"
    for_ui = "UI Interactive"


# This is a dependency to validate the user by token. It depends on the "get_current_user_by_token" function from crud.py
# which validates current user by token (the token will be stored in cookies).
user_dependency = Annotated[UserInDB, Depends(get_current_user_by_token)]


# Create A JWT Token
@app.post("/token", tags=[Tags.for_token], response_model=Token, description="A POST method that returns current user's token.")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    The login_for_access_token is one of the most IMPORTANT function in this project (this is the reason why I put on the top of every other REST API methods).

    Logic:
    1. It receives an OAuth2PasswordRequestForm and authenticate user by using authenticate_user function from auth.py.
    2. If user is None, it will raise a HTTPException that mentions current user failed self-authentication.
    3. Otherwise, it will create an access token by calling 'create_access_token' function from auth.py.
    4. It returns a dictionary that contains 'access_token' and 'token_type.'
    """

    user = await authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect Login ID or Password.",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user["login_id"]}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


# Main Homepage
@app.get("/index", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that visualizes the main home page.")
async def index(request: Request):
    """
    Logic:
    1. First, it receives a request and checks if our current request contains a JWT Token (we use request.cookies.get function to check if token exists in our current request).
     - If our JWT Token exists, we first eliminate a partial string called 'Bearer' from our token by using replace function.
     - We use 'jwt.decode' function to check if our current JWT Token is expired.
    2. If it's expired, it will raise ExpiredSignatureError, and we update our 'user_status' string to 'Your token has expired. Login again!'
    3. Otherwise, we use get_current_user_by_token function to get our current user's info (this will return UserInDB object), update our 'user_status' string with greeting message
     - 'need_to_login' boolean variable will change to False because we don't need to log in again.
    4. Finally, it will return a 'TemplateResponse' (an 'index.html' file) with including 'user_status' and 'need_to_login' variables as a context (the context will be used as a variable from HTML).
    """

    user_status = "Sign up or Login!"
    current_token = request.cookies.get("access_token")
    need_to_login = True
    if current_token is not None:
        current_token = current_token.replace("Bearer ", "")  # should eliminate "Bearer " from our token when we want to decode (validate) our current token
        try:
            jwt.decode(current_token, SECRET_KEY, ALGORITHM)
            current_user = await get_current_user_by_token(current_token)
            user_status = f'Hello, {current_user["login_id"]}.'
            need_to_login = False
        except exceptions.ExpiredSignatureError:
            user_status = f'Your token has expired. Login again!'
    return templates.TemplateResponse("index.html", context={"request": request, "user_status": user_status, "need_to_login": need_to_login})


# Sign Up Page
@app.get("/sign_up", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that visualizes the sign up page.")
async def sign_up(request: Request):
    """
    The 'sign_up' function simply visualizes the 'sign_up.html' HTML file by returning TemplateResponse.
    """
    return templates.TemplateResponse("sign_up.html", context={"request": request})


# Create User
@app.post("/create-user", tags=[Tags.for_user], response_class=HTMLResponse, description="A Post method that creates an UserCreate object, convert to UserInDB object, and store it in our database.")
async def create_one_user(request: Request):
    """
    The 'create_one_user' function creates an UserCreate and convert it into UserInDB object and store it into our database.

    Logic:
    1. First, it will define the response into RedirectResponse with status code 302 (it will re-direct to "/index" path which is our main homepage).
    2. Then, it will get data by using request.form() to export every data that are stored in request.
    3. Next, it will create a UserCreate object and pass it into our 'create_user' function from crud.py to store user's data in UserInDB object.
    4. If the 'create_user' function returns None, it will raise an HTTPException which means current 'login_id' is already exists in our database so user should use different login id.
    5. Otherwise, it will just return a RedirectResponse which makes user to login again (in this process, the program will NOT generate a JWT Token and force the user to login).
    """

    response = RedirectResponse("/index", status.HTTP_302_FOUND)
    form_data = await request.form()
    new_user_create = UserCreate(login_id=form_data["login_id"],
                                 email=form_data["email"],
                                 birth_date=form_data["birth_date"],
                                 sex=form_data["sex"],
                                 full_name=form_data["full_name"],
                                 password=form_data["password"]
                                 )
    new_user_message = await create_user(new_user_create)
    if new_user_message == "duplicate login_id":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Login ID: {new_user_create.login_id} is already registered. Please use a different Login ID.")
    if new_user_message == "duplicate email":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Email: {new_user_create.email} is already registered. Please use a different email.")
    return response


# Login Page
@app.get("/login", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that visualizes the log in page.")
def login_get(request: Request):
    """
    The 'login_get' function simply visualizes the 'login.html' HTML file to let the user type their login id and password to log in and receive the JWT access token.
    """

    context = {"request": request}
    return templates.TemplateResponse("login.html", context=context)


# Login
@app.post("/login_result", tags=[Tags.for_user], response_class=HTMLResponse, description="A POST method that creates a JWT Token.")
async def login_result(request: Request):
    """
    The 'login_result' function returns a RedirectResponse with status code 302. It will raise an HTTPException if user types a wrong login id/ password OR non-existing login id.

    Logic:
    1. First, it will create a RedirectResponse object with url: "/index" (main homepage) and a status code 302.
    2. Then, it will export data that are stored in request by using form().
    3. Next, the value with a key 'login_id' will be a parameter of 'username' and a value with a key 'password' will be a parameter of 'password' from OAuth2PasswordRequestForm.
    4. After that, it will call 'login_for_access_token' function to create an access token by using current user's personal data.
    5. IMPORTANT! After step 4, the program should store the current user's access token into the cookie, so it will use the 'set_cookie' function to store the JWT Token into the cookie.
     - The cookie's key will be the string 'access_token' and the value will be the string 'Bearer ' + current JWT Token. The 'httponly' parameter should be True to prevent from XSS attack.
    6. Finally, it will return the RedirectResponse.
    """

    response = RedirectResponse("/index", status.HTTP_302_FOUND)
    form_data = await request.form()
    request_form = OAuth2PasswordRequestForm(username=form_data["login_id"], password=form_data["password"])
    token_obj = await login_for_access_token(request_form)
    response.set_cookie(key="access_token", value=f'Bearer {token_obj["access_token"]}', httponly=True)
    return response


# Read One User's Personal Information
async def read_one_user_personal_info(current_user: user_dependency) -> dict:
    """
    This function was previously a GET method -> @app.get("/my-personal-info", tags=[Tags.for_user], response_model=dict)
    However, now it is just a function that returns current user's personal information as a dictionary format.
    The parameter 'current_user' is a UserInDB object that has a dependency of 'get_current_user_by_token' function from auth.py.
    User's hashed password will not be included in the dictionary because it is unnecessary to return user's hashed password.
    """

    return {"login_id": current_user["login_id"],
            "email": current_user["email"],
            "birth_date": current_user["birth_date"],
            "sex": current_user["sex"],
            "full_name": current_user["full_name"]
            }


# Read One User's Current Mileage
async def read_one_user_mileage(current_user: user_dependency):
    """
    This function was a previously a GET method -> @app.get("/my-mileage", tags=[Tags.for_user], response_model=str)
    However, now it is just a function that returns current user's mileage as an integer format.
    It has the same parameter as the 'read_one_user_personal_info' function.
    """

    return current_user["mileage"]


# Private Page
@app.get("/private", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that visualizes user's private information.")
async def private(request: Request):
    """
    The 'private' function export the JWT Token from the request and use it as a 'user dependency' to get user's private information, the amount of mileage, and every ticket.

    Logic:
    It calls four different functions.
    1. Calls 'get_current_user_by_token' to get the JWT Token.
    2. Calls 'read_one_user_personal_info' to get current user's information.
    3. Calls 'read_one_user_mileage' to get current user's mileage.
    4. Calls 'read_all_tickets' to get current user's every ticket.
    5. Initializes the 'show_cancel_menu' variable to 'True' and if the dictionary that we received from 'read_all_tickets' includes the "message" string as a key -> re-initialize to False.
       - The reason why we need 'show_cancel_menu' variable is, we don't want to visualize the ticket cancel menu to our user if user has 0 tickets.
    6. Create a dictionary to use these data from our 'private.html' HTML file and pass this to our TemplateResponse as a context.
    7. Finally, return the TemplateResponse to visualize these data by using 'private.html' HTML file (redundant explanation but want to make it clear).
    """

    if not request.cookies:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"message": "login first"})
    user = await get_current_user_by_token(request.cookies['access_token'])
    user_info = await read_one_user_personal_info(user)
    user_mileage = await read_one_user_mileage(user)
    user_tickets = await read_all_tickets(user)
    show_cancel_menu = True
    if "message" in user_tickets.keys():
        show_cancel_menu = False
    context = {
        "request": request,
        "login_id": user_info["login_id"],
        "email": user_info["email"],
        "birth_date": user_info["birth_date"],
        "sex": user_info["sex"],
        "full_name": user_info["full_name"],
        "user_mileage": user_mileage,
        "user_tickets": user_tickets,
        "show_cancel_menu": show_cancel_menu
    }
    return templates.TemplateResponse("private.html", context=context)


# Delete User's Account
async def delete_one_user(current_user: user_dependency):
    """
    This function was previously a DELETE method -> @app.delete("/delete-my-account", tags=[Tags.for_user], response_model=str)
    It calls 'cancel-every_ticket' and 'delete_user' function to delete current user's every ticket and information.
    It returns a string that mentions the current user's account has been deleted (It's for debugging purpose).
    """

    is_gone = await cancel_every_ticket(current_user) + " " + await delete_user(current_user)
    return is_gone


# Delete User's Account Page
@app.get("/delete-my-account-get", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that visualizes a confirm page to delete user's account.")
async def delete_one_user_get(request: Request):
    """
    The 'delete_one-user_get_before' function simply visualizes a confirmation page to re-check that user made a correct decision about deleting his/her account.
    It returns a TemplateResponse to show the 'delete_account.html' HTML file.
    """

    context = {"request": request}
    return templates.TemplateResponse("delete_account.html", context=context)


# Delete User's Account
@app.post("/delete-my-account-post-confirm", tags=[Tags.for_user], response_class=HTMLResponse, description="A POST method that deletes current user's account.")
async def delete_one_user_post(request: Request):
    """
    The 'delete_one_user_post' function calls two different functions and delete current user's account.

    Logic:
    1. Calls 'get_current_user_by_token' function to get current user's JWT Token.
    2. Calls 'delete_one_user' function to delete current user's data from database (this is located in crud.py).
    3. Initialize a RedirectResponse that redirects to the main homepage.
    4. Calls 'delete_cookie' function to delete current JWT Token that is stored in current cookie.
    5. Return RedirectResponse.
    """

    user = await get_current_user_by_token(request.cookies["access_token"])
    await delete_one_user(user)
    response = RedirectResponse("/index", status.HTTP_302_FOUND)
    response.delete_cookie('access_token')
    return response


# Create A Ticket Page
@app.get("/create-ticket-get", tags=[Tags.for_user], response_class=HTMLResponse, description="A GET method that visualizes the create ticket page.")
async def create_ticket_get(request: Request):
    """
    The 'create_ticket_get' function simply returns the TemplateResponse that visualizes some input boxes to type in the information of flight that user want
    to book. It's very similar as the 'sign_up' function.
    """

    return templates.TemplateResponse("create_ticket.html", context={"request": request})


# Create A Ticket
@app.post("/create-ticket", tags=[Tags.for_ticket], response_class=HTMLResponse, description="A POST method that creates a ticket and store it into the database.")
async def create_one_ticket(request: Request):
    """
    The 'create_one_ticket' function receives specific information of a certain flight that user booked. It returns a RedirectResponse after successfully create a ticket.

    Logic:
    1. First, define a RedirectResponse that will be returned after successfully create a ticket.
    2. Then, export specific data from request by using 'form' built-in function (this is from starlette framework).
    3. Next, create a 'TicketCreate' object with using data from request.form().
    4. Call 'get_current_user_by_token' to get current JWT Token.
    5. Call 'create_ticket' by sending the JWT Token and 'TicketCreate' object as a parameter to store the new ticket into the database.
    6. If there is a conflict (if user already has a flight on the day that he/she selected to book a new ticket, it will raise an HTTPException).
       - The departure data is UNIQUE: user should select another departure date!
    """

    response = RedirectResponse("/private", status.HTTP_302_FOUND)
    form_data = await request.form()
    new_ticket_create = TicketCreate(starting_point=form_data["starting_point"],
                                     ending_point=form_data["ending_point"],
                                     departure_date=form_data["departure_date"],
                                     jet_type=form_data["jet_type"])
    current_user = await get_current_user_by_token(request.cookies["access_token"])
    new_ticket_message = await create_ticket(current_user, new_ticket_create)
    if new_ticket_message is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Invalid Ticket Information: "
                                                                         f"Check your flight schedule on {new_ticket_create.departure_date} (You can't book two flights per day)."
                                                                         f"Check the starting and ending points (They should be different).")
    return response


# Get Every Ticket
@app.get("/my-tickets", tags=[Tags.for_ticket], response_model=dict, description="A GET method that reads every ticket.")
async def read_all_tickets(current_user: user_dependency):
    """
    The 'read_all_tickets' function reads every ticket. However, it doesn't read the entire tickets from the database: it only reads tickets that contains current user's login id
    as an owner_id (every TicketInDB object includes 'owner_id' and it will check through the 'read_every_ticket' function from crud.py).
    """

    my_tickets = await read_every_ticket(current_user)
    if not my_tickets:
        return {"message": "You don't have any tickets!"}
    return my_tickets


# Cancel Tickets Page
@app.get("/cancel-tickets-get", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that visualizes two selections to cancel tickets.")
async def cancel_tickets_get(request: Request):
    """
    The 'cancel_tickets_get' function visualizes two different options to cancel tickets.

    Logic:
    1. Call 'get_current_user_by_token' to get current JWT Token.
    2. Call 'read_every_ticket' function to get every ticket that user owns.
    3. Return the TemplateResponse to visualize the 'cancel_tickets.html' HTML file.
       - Every ticket will be sent as a dictionary format, and it will be a part of context to visualize from HTML file.
    """

    user = await get_current_user_by_token(request.cookies["access_token"])
    user_tickets = await read_every_ticket(user)
    context = {"request": request, "user_tickets": user_tickets}
    return templates.TemplateResponse("cancel_tickets.html", context=context)


# Cancel Every Ticket
async def cancel_all_tickets(current_user: user_dependency):
    """
    The 'cancel_all_tickets' was previously a DELETE method -> @app.delete("/cancel-every-ticket", tags=[Tags.for_ticket], response_model=str)
    It calls the 'cancel_every_ticket' function by passing the 'user_dependency' as a parameter to check the owner_id class attribute from TicketInDB object.
    It will ONLY delete every 'TicketInDB' object that contains current user's login_id as an owner_id (again, owner_id is a class attribute from TicketInDB object [super important]).
    """

    is_all_gone = await cancel_every_ticket(current_user)
    return is_all_gone


# Cancel Every Ticket And Redirect To Main Homepage
@app.post("/cancel-every-ticket-post-confirm", tags=[Tags.for_ui], response_class=HTMLResponse, description="A POST method that cancel every ticket.")
async def cancel_all_tickets_post_confirm(request: Request):
    """
    The 'cancel_all_tickets_post_confirm' is a POST method that calls the 'cancel_all_ticket' function and redirect to the main homepage.
    The 'cancel_all_tickets' function returns a string to check if tickets are successfully deleted (this is for debugging purpose).
    """

    response = RedirectResponse("/private", status.HTTP_302_FOUND)
    user = await get_current_user_by_token(request.cookies["access_token"])
    message = await cancel_all_tickets(user)
    print(message)
    return response


# Cancel One Ticket
async def cancel_one_ticket(cancel_date: str, current_user: user_dependency):
    """
    The 'cancel_one_ticket' was previously a DELETE method -> @app.delete("/cancel-one-ticket", tags=[Tags.for_ticket], response_model=str)
    It has a similar logic as the 'cancel_all_tickets' function. However, it requires a specific date (a departure date).
    """

    is_gone = await cancel_ticket_by_departure_date(cancel_date, current_user)
    return is_gone




@app.post("/cancel-one-ticket-post-confirm", tags=[Tags.for_ui], description="A POST method that cancels one ticket.")
async def cancel_one_ticket_post_confirm(request: Request):
    """
    The 'cancel_one_ticket_post_confirm' function has a similar logic as the 'cancel_all_tickets_post_confirm' function.
    However, it exports the 'departure_date' data from the request.form().
    If 'cancel_one_ticket' function returns None, it will raise a HTTPException which means there is no flight on a certain date that user typed in to cancel a ticket.
    Logic Explanation is omitted because it's almost same as the 'cancel_all_tickets_post_confirm' (the difference is, it requires a specific 'cancel_date').
    """

    response = RedirectResponse("/private", status.HTTP_302_FOUND)
    form_data = await request.form()
    cancel_date = form_data["cancel_date"]
    user = await get_current_user_by_token(request.cookies["access_token"])
    is_gone = await cancel_one_ticket(cancel_date, user)
    if is_gone is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"You don't have a flight on {cancel_date}")
    return response


# Logout Process
@app.get("/logout", tags=[Tags.for_ui], response_class=HTMLResponse, description="A GET method that redirects to main homepage.")
async def logout():
    """
    The 'logout' function simply returns a RedirectResponse (redirect to the main homepage).
    Before it redirects, it will delete the current JWT Token by using 'delete_cookie' function.
    """

    response = RedirectResponse("/index")
    response.delete_cookie('access_token')
    return response


# PUT methods (will be updated [maybe???]) ####################################################################################################
# update user's email
# @app.put("/change-my-email-to", tags=[Tags.for_user], response_model=str)
# async def update_one_user_info(current_user: user_dependency, update_request: EmailUpdateRequest):
#     has_changed = await update_user_email(current_user, update_request)
#     return has_changed
#
#
#
# update user's specific ticket's jet type (this will be updated later)
# @app.put("/change-my-jet", tags=[Tags.for_ticket], response_model=str)
# async def update_one_ticket_jet_type(current_user: user_dependency, update_request: JetTypeUpdateRequest):
#     has_changed = await update_jet_type(current_user, update_request)
#     return has_changed
# PUT methods (will be updated [maybe???]) ####################################################################################################


# Methods for debugging purpose (can access the MongoDB without user_dependency) ####################################################################################################
# @app.delete("/delete-without-dependency", tags=["Debug"])  # created for debugging
# async def delete_without_user_dependency(user_id: str):
#     return await delete_user_with_id(user_id)
