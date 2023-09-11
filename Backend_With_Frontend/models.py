from pydantic import BaseModel, EmailStr


class TicketBase(BaseModel):
    """
    The 'TicketBase' pydantic model includes...
    1. 'starting_point' (Departure)
    2. 'ending_point' (Destination)
    3. 'departure_date' (The Date Of Departure)
    4. 'jet_type' (The Type Of Private Jet)

    * IMPORTANT
    The 'starting_point' and 'ending_point' are string type variables, and they will use an IATA 3-letter codes for airport.
    The 'departure_date' is a string type variable with following format: YYYY-MM-DD.
    The 'jet_type' is a string type variable.
    """

    starting_point: str
    ending_point: str
    departure_date: str
    jet_type: str


class TicketCreate(TicketBase):
    """
    The 'TicketCreate' pydantic model inherits the 'TicketBase.'
    """
    pass


class TicketInDB(TicketBase):
    """
    The 'TicketInDB' pydantic model is a model that will be stored in the database.
    It inherits the 'TicketBase' model and additional has a 'owner_login_id' class variable to state the ticket's owner id.
    The __eq__ function let the program compare tickets with each other. It checks each of ticket's class variables and if they are all same, it returns True.
    """

    owner_login_id: str  # this is same as the user's 'login_id'

    def __eq__(self, other):
        return self.starting_point == other.starting_point and self.ending_point == other.ending_point and self.departure_date == other.departure_date and self.jet_type == other.jet_type


class UserBase(BaseModel):
    """
    The 'UserBase' is a pydantic model that contains user's personal information...
    1. 'login_id' (User's login id is required to log in the system)
    2. 'email' (User's email. It uses an 'EmailStr' class which pydantic provides to validate the format of email. Exception occurs if user forgot to add '@' in user's email)
    3. 'birth_date' (User's birthdate. The format is 'YYYYMMDD' but the system does not raise an exception if user inputs a different format while signing in) *** this should be improved
    4. 'sex' (User's sex. User can pick one of the gender 'male' or 'female')
    5. 'full_name' (User's full name)

    * IMPORTANT
    - 'login_id' and 'email' are unique variables. Every user will have one unique 'login_id' and 'email'.
    - 'email' is a 'EmailStr' type, but it's still a string variable.
    - Every variable can be duplicated from the database except 'login_id' and 'email'.
    """

    login_id: str
    email: EmailStr
    birth_date: str
    sex: str
    full_name: str


class UserCreate(UserBase):
    """
    The 'UserCreate' pydantic model inherits the 'UserBase' model. It has a password class variable as a string, and it will be
    used when a new user try to sign in.
    """

    password: str


class UserInDB(UserBase):
    """
    The 'UserInDB' pydantic model also inherits the 'UserBase' model. It has two class variables which are 'hashed_password' and 'mileage'

    1. 'hashed_password' (It's a 'bytes' type variable. The system will hash user's pure password and store it into the database)
    2. 'mileage' (It's an integer type variable. It is initialized to 0 because every user who signed in to this system will start from 0 mileages)

    * IMPORTANT
    - The system should not store user's pure password into the database for the security.
    """

    hashed_password: bytes
    mileage: int = 0  # new user's mileage starts from 0


class Token(BaseModel):
    """
    The 'Token' pydantic model will be used when user logins and receives an access JWT Token.
    It includes two string type variables.

    1. 'access_token' (It is a string type variable, but it is actually a JWT Token)
    2. 'token_type' (The type of token will be a 'Bearer,' and this will be stored in a string)
    """

    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    The 'TokenData' pydantic model includes user's login_id. This will be used in auth.py for checking user's existence.
    """

    login_id: str


# These pydantic model will be used in the updating process [maybe???].
# class EmailUpdateRequest(BaseModel):
#     new_email: EmailStr
#
#
# class JetTypeUpdateRequest(BaseModel):
#     departure_date: str
#     new_jet_type: str
