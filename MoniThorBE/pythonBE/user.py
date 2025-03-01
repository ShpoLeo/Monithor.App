from psycopg2 import Error
from logger.logs import logger
from pythonBE.dbconnection import get_db_connection

def register_user(userName, password1, password2):
    logger.debug(f'Register Functions is invoked with new User:{userName}')
    successMessage = {'message': "Registered successfully"}
    failureMessage = {'message': "Username already taken"}
    emptyMessage = {'message': "Username or password is Empty"}
    passwordMessage = {'message': "Passwords do not match"}
    dbErrorMessage = {'message': "Database error occurred"}

    # check if the user name and password empty 
    if not userName or not password1 or not password2:
        return emptyMessage
    
    if password1 != password2:
        return passwordMessage

    connection = get_db_connection()
    if not connection:
        logger.error("Failed to establish database connection")
        return dbErrorMessage

    try:
        cursor = connection.cursor()

        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE username = %s", (userName,))
        if cursor.fetchone():
            return failureMessage

        # Insert new user
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (userName, password1)
        )
        connection.commit()
        logger.info(f'New User is created - username: {userName}')
        return successMessage

    except Error as e:
        logger.error(f"Database error: {e}")
        return {'message': "Database error occurred"}
    finally:
        if connection:
            cursor.close()
            connection.close()

def login_user(userName, password):
    logger.debug(f'Login Functions is invoked with User:{userName}')
    successMessage = {'message': "Login Successful"}
    failureMessage = {'message': "error : invalid user name or password"}

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT username FROM users WHERE username = %s AND password = %s",
            (userName, password)
        )
        if cursor.fetchone():
            return successMessage
        return failureMessage

    except Error as e:
        logger.error(f"Database error: {e}")
        return failureMessage
    finally:
        if connection:
            cursor.close()
            connection.close()

def is_user_exist(userName):
    logger.debug(f'Checking if user {userName} exist')
    successMessage = {'message': "User exist"}
    failureMessage = {'message': "User or User file is not exist"}

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT username FROM users WHERE username = %s", (userName,))
        if cursor.fetchone():
            return successMessage
        return failureMessage

    except Error as e:
        logger.error(f"Database error: {e}")
        return failureMessage
    finally:
        if connection:
            cursor.close()
            connection.close()
