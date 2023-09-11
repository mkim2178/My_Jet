from database import user_collection
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Annotated
from models import TokenData


"""
Reference Link: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/.
Technically, I used almost every code from the reference link because this is the first time that I'm studying security (authentication).
The reference uses the 'OAuth2' and JWT Token for the security.
"""


# This is a secret key for the JWT Token. It is a random string and I got this by using following command: openssl rand -hex 32
# In my opinion, this secret key should be hidden somewhere, but I just initialized in this file to comfortably use it for debugging purpose OR from several functions.
SECRET_KEY = "a909dbfad5cc941fc277e3ec56efd63aadafed50197baab4a35ab4a4a4914a51"


# The 'HS256' is a name of algorithm that will be used to create a secret key for user to interact this program.
ALGORITHM = "HS256"


# The JWT Token expiration time will be set to 10 minutes. After 10 minutes, the JWT Token will be expired and user should receive a refresh JWT Token by re-login.
ACCESS_TOKEN_EXPIRE_MINUTES = 10


"""
schemes=["bcrypt"]
- The 'CryptContext' class is from passlib.context library. It helps the program to hash password by using specific algorithms.
- The 'schemes' parameter is a list that program will use as an algorithm to hash the password.
- In this program, 'bcrypt' algorithm will be used.

deprecated="auto"
- This will configure the CryptContext instance to deprecated every scheme that are supported.
"""
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# The program will use the 'OAuth2PasswordBearer' dependency, and it will return a JSON response such as {"access_token": access_token", "token_type": bearer} if
# we pass in the 'tokenUrl,' "token." This dependency is one of the most important part of this project because it will be used on every user authentication.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def check_password(password, hashed_password):
    """
    This function has two parameters: the pure password and the hashed password.
    It will use the 'verify' CryptContext's function to check if the "password verifies against the hash." -> this quoted sentence is from the context.py (passlib)
    It will return True if password is verified, otherwise, return False.
    """

    return pwd_context.verify(password, hashed_password)


def get_hashed_password(password):
    """
    This function uses the 'hash' CryptContext's function to hash the pure password.
    It will return a string (which is a hashed password).
    """
    return pwd_context.hash(password)


async def get_user_by_login_id(user_login_id):
    """
    This function will return None if user is not existing in the user database.
    It simply uses the 'find_one' pymongo function by using the 'user_login_id' as a condition.
    If it returns None, return None. Otherwise, it will return the user.
    """

    searched_user = await user_collection.find_one({"login_id": user_login_id})
    if not searched_user:
        return None
    return searched_user


async def authenticate_user(user_login_id: str, user_password: str):
    """
    This function will call the 'get_user_by_login_id' to check if user exists in our user database by using user's 'login_id'.
    Then it will call the 'check_password' function to check the input 'user_password' is a correct password.
    If this function returns the user ('UserInDB' model), this means the user authentication has been successfully verified.
    Otherwise, it will return None which means user failed about authenticating him/her self.
    """

    user = await get_user_by_login_id(user_login_id)
    if not user:
        return None
    if not check_password(user_password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    This function will create an access token for the user.

    Logic:
    1. First, it will copy every data from 'data' dictionary.
    2. Then, if the 'expires_delta' is not None, the 'expire' variable will be initialized as current datetime + expires_delta (remaining expiration time).
       - If the 'expires_delta' is None, which means if current token has expired, the 'expire' will add additional 15 minutes to the token (datetime object).
    3. After that, it will use the 'update' python built-in function to update the "exp" attribute.
    4. Next, it will use the 'encode' jwt function by passing encode_data (updated data), the secret key (JWT Token), and the current algorithm.
    5. Finally, it will return the encoded JWT Token (the information from step 4).
    """

    encode_data = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    encode_data.update({"exp": expire})
    encode_jwt = jwt.encode(encode_data, SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt


async def get_current_user_by_token(token: Annotated[str, Depends(oauth2_scheme)]):  # get_current_user_from_token
    """
    This function is one of the most important functions from auth.py file. It brings every information from database by using current JWT Token.

    Logic:
    1. First, the parameter 'token' has a dependency of 'oauth2_scheme' that is initialized from the beginning of auth.py file.
    2. Then, it creates an HTTPException for the credential exception that can potentially occur during this function.
    3. Next, it will use a try and except exception handler to check user credential validation.
       1) First, it will try to decode the token (it should replace the "Bearer " string from the token) because the 'decode' jwt function only requires a JWT Token.
       2) Then, it will define a local variable 'login_id' by using the 'get' python built-in function to get the information (user's login id) from the JWT Token's payload.
       3) If 'login_id' is None, it will raise a HTTPException. Otherwise, the 'TokenData' pydantic model will be created and the 'login_id' will be the parameter of this object
          - This means the 'TokenData' pydantic model's class attribute 'login_id' will be defined by using local variable 'login_id' that is created on line 144.
    4. After that, it will call the 'get_user_by_login_id' to get current user.
    5. If step 4 returns None, it will also raise a HTTPException, which means user does not exist who uses this 'login_id'.
    6. Finally, it will return the user's information by a dictionary format.
    """

    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                         detail="couldn't validate credentials",
                                         headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token.replace("Bearer ", ""), SECRET_KEY, algorithms=ALGORITHM)
        login_id: str = payload.get("sub")
        if login_id is None:
            raise credential_exception
        token_data = TokenData(login_id=login_id)
    except JWTError:
        raise credential_exception
    user = await get_user_by_login_id(user_login_id=token_data.login_id)
    if user is None:
        raise credential_exception
    return user
