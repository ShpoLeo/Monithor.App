import os
import re
from logger.logs import logger
from psycopg2 import Error
from pythonBE.dbconnection import get_db_connection

def add_domain(userName, domain):
    logger.debug(f'Function is invoked {userName}, {domain}')
    successMessage = {'message': "Domain successfully added"}
    failureMessageExist = {'message': "Domain already exists"}
    failureMessageNotValid = {'message': "Invalid Domain Name"}
    dbErrorMessage = {'message': "Database error occurred"}
    
    domain = domain.replace('"', '')
    
    if not is_valid_domain(domain):
        return failureMessageNotValid

    connection = get_db_connection()
    if not connection:
        logger.error("Failed to establish database connection")
        return dbErrorMessage

    try:
        cursor = connection.cursor()

        # Get user_id first
        cursor.execute("SELECT id FROM users WHERE username = %s", (userName,))
        user_result = cursor.fetchone()
        if not user_result:
            return {'message': "User not found"}
        user_id = user_result[0]

        # Check domain count for user
        cursor.execute(
            "SELECT COUNT(*) FROM user_domains WHERE user_id = %s",
            (user_id,)
        )
        if cursor.fetchone()[0] >= 100:
            return {'message': "Maximum domain limit reached"}

        # Check if domain exists in domains table
        cursor.execute("SELECT id FROM domains WHERE domain = %s", (domain,))
        domain_result = cursor.fetchone()
        
        if domain_result:
            domain_id = domain_result[0]
            # Check if user already has this domain
            cursor.execute(
                "SELECT 1 FROM user_domains WHERE user_id = %s AND domain_id = %s",
                (user_id, domain_id)
            )
            if cursor.fetchone():
                return failureMessageExist
        else:
            # Insert new domain
            cursor.execute(
                """INSERT INTO domains (domain, status, ssl_expiration, ssl_issuer) 
                VALUES (%s, %s, %s, %s) RETURNING id""",
                (domain, 'unknown', 'unknown', 'unknown')
            )
            domain_id = cursor.fetchone()[0]

        # Create user-domain relationship
        cursor.execute(
            "INSERT INTO user_domains (user_id, domain_id) VALUES (%s, %s)",
            (user_id, domain_id)
        )
        
        connection.commit()
        logger.debug(f'The {domain} added to database for user {userName}')
        return successMessage

    except Error as e:
        logger.error(f"Database error: {e}")
        return dbErrorMessage
    finally:
        if connection:
            cursor.close()
            connection.close()



def remove_domain(userName, domain):
    logger.debug(f'Function is invoked {userName}, {domain}')
    successMessage = {'message': "Domain successfully removed"}
    notInDbMessage = {'message': "Domain not found"}
    failureMessageNotValid = {'message': "Invalid Domain Name"}
    dbErrorMessage = {'message': "Database error occurred"}
    
    domain = domain.replace('"', '')
    
    if not is_valid_domain(domain):
        return failureMessageNotValid

    connection = get_db_connection()
    if not connection:
        logger.error("Failed to establish database connection")
        return dbErrorMessage

    try:
        cursor = connection.cursor()
        
        # Get user_id and domain_id
        cursor.execute("SELECT id FROM users WHERE username = %s", (userName,))
        user_result = cursor.fetchone()
        if not user_result:
            return {'message': "User not found"}
        user_id = user_result[0]

        cursor.execute("SELECT id FROM domains WHERE domain = %s", (domain,))
        domain_result = cursor.fetchone()
        if not domain_result:
            return notInDbMessage
        domain_id = domain_result[0]
        
        # Delete from user_domains
        cursor.execute(
            "DELETE FROM user_domains WHERE user_id = %s AND domain_id = %s RETURNING id",
            (user_id, domain_id)
        )
        if cursor.fetchone():
            connection.commit()
            return successMessage
        return notInDbMessage

    except Error as e:
        logger.error(f"Database error: {e}")
        return dbErrorMessage
    finally:
        if connection:
            cursor.close()
            connection.close()

# function to read from file a list of domain and add to domain file.

def add_bulk(userName, fileName):
    fileName = fileName.replace('"', '')
    logger.debug(f"File: {fileName}, User: {userName}")
    
    if not os.path.exists(fileName):
        return "File Not Exist"
    
    try:
        with open(fileName, 'r') as infile:
            for line in infile:
                add_domain(userName, line.strip())
    
    except Exception as e:
        return str(e)
     
    return "Bulk upload finished"






# Function to validate the domain name

def is_valid_domain(s):    
    # Regex to check valid Domain Name
    pattern= r"^(([a-zA-Z]{1})|([a-zA-Z]{1}[a-zA-Z]{1})|([a-zA-Z]{1}[0-9]{1})|([0-9]{1}[a-zA-Z]{1})|([a-zA-Z0-9][a-zA-Z0-9-_]{1,61}[a-zA-Z0-9]))\.([a-zA-Z]{2,6}|[a-zA-Z0-9-]{2,30}\.[a-zA-Z]{2,3})$"         
    
    # Return string matche value - bool
    return bool(re.match(pattern,s))





