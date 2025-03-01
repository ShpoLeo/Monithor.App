from flask import Flask,request, jsonify
from pythonBE import user , check_liveness ,domain
from logger.logs import logger
import json
import os
from datetime import datetime 
from flask_cors import CORS
from logger.utils  import Utils
from elasticapm.contrib.flask import ElasticAPM
import logging
from psycopg2 import connect, Error
from pythonBE.dbconnection import get_db_connection

utils = Utils()

# Set up APM debugging
logging.getLogger('elasticapm').setLevel(logging.DEBUG)

app = Flask(__name__)  # __name__ helps Flask locate resources and configurations

app.config['ELASTIC_APM'] = {
  'SERVICE_NAME': 'Monothor-be',
  'API_KEY': 'RmY0Q0NaVUJLaTZSRzdmcEpuU0c6REhuQnp4M3poRDZHSHZlRGxHdHo5Zw==',
  'SERVER_URL': 'https://my-observability-project-bbb56a.apm.us-west-2.aws.elastic.cloud:443',
  'ENVIRONMENT': 'Test',
  'TRANSACTIONS_SAMPLE_RATE': 1.0,
  'DEBUG': True,
}

apm = ElasticAPM(app, logging=True)


CORS(app)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)
    app.config.update(config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global parmeters to keep last job info.
global globalInfo 
globalInfo = {'runInfo': ('--/--/---- --:--', '-')} 


# Route for BE login  
@app.route('/BElogin', methods=['POST'])
@utils.measure_this
def BElogin():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        logger.debug(f"Attempt to login with - User: {username}, Pass: {password}")
        
        status = user.login_user(username, password)
        if status['message'] == "Login Successful":
            
            
            logger.info(f"User: {username} Login Successful")
            return jsonify({"message": "Login Successful"})
        else:
            logger.info(f"User: {username} Login Failed")
            return jsonify({"message": "Invalid username or password!"}), 401
    return jsonify({"message": "Bad Request"}), 400



@app.route('/BElogin_lc', methods=['GET'])
@utils.measure_this
def BElogin_lc():   
    
    username = 'locust'# data.get('username')
    password = 'locust'# data.get('password')
        
    logger.debug(f"Attempt to login with - User: {username}, Pass: {password}")        
    status = user.login_user(username, password)
    if status['message'] == "Login Successful":                      
        logger.info(f"User: {username} Login Successful")
        return jsonify({"message": "Login Successful"})
    else:
        logger.info(f"User: {username} Login Failed")
        return jsonify({"message": "Invalid username or password!"}), 401
    


@app.route('/BEresults/<username>', methods=['GET'])
@utils.measure_this
def BEresults(username):
    logger.debug(f'BEresults function called for user: {username}')
    
    if user.is_user_exist(username)['message'] != "User exist":
        logger.debug(f'User {username} does not exist')
        return "No User is logged in"

    connection = get_db_connection()
    if not connection:
        logger.error("Failed to establish database connection")
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = connection.cursor()
        
        # Get user_id
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            logger.debug(f'User {username} not found in database')
            return jsonify({"error": "User not found"}), 404
        user_id = user_result[0]

        # Get all domains for this user with their status
        logger.debug(f'Fetching domains for user_id: {user_id}')
        cursor.execute("""
            SELECT 
                d.domain,
                d.status,
                d.ssl_expiration::text,
                d.ssl_issuer
            FROM domains d
            JOIN user_domains ud ON d.id = ud.domain_id
            WHERE ud.user_id = %s
            ORDER BY d.id DESC
        """, (user_id,))
        
        results = cursor.fetchall()
        
        # Format the data
        data = [{
            'domain': row[0],
            'status_code': row[1],
            'ssl_expiration': row[2],
            'ssl_issuer': row[3]
        } for row in results]

        all_domains = [item['domain'] for item in data]
        latest_results = data[:6]
        failuresCount = sum(1 for item in data if item.get('status_code') == 'FAILED')
        
        failuresPrecent = round(float(failuresCount) / len(all_domains) * 100, 1) if len(all_domains) > 0 else 0
        
        # Handle the case where globalInfo might not be available
        try:
            lastRunInfo = f"{globalInfo['runInfo'][0]}, {globalInfo['runInfo'][1]} Domains, {failuresPrecent}% failures"
        except (NameError, KeyError):
            lastRunInfo = f"Last Run Info Not Available, {len(all_domains)} Domains, {failuresPrecent}% failures"

        logger.debug(f'Successfully prepared response for user {username} with {len(all_domains)} domains')

        response = {
            'user': username,
            'data': data,
            'all_domains': all_domains,
            'latest_results': latest_results,
            'last_run': lastRunInfo
        }
        
        return jsonify(response)

    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({"error": "Database error occurred"}), 500
    finally:
        if connection:
            cursor.close()
            connection.close()
    


@app.route('/BEregister', methods=['POST','GET'])
@utils.measure_this
def BEregister():
    
    data = request.get_json()
    username = data.get('username')
    password1 = data.get('password1')
    password2 = data.get('password2')   

    # Validate input parameters
    if not username or not password1 or not password2:
        return jsonify({"error": "All fields are required"}), 400
    if password1 != password2:
        return jsonify({"error": "Passwords do not match"}), 400

    # Process registration
    status = user.register_user(username, password1, password2)

    if status['message'] == 'Username already taken':
        return jsonify({"error": "Username already taken"}), 409
    if status['message'] == 'Registered successfully':
        return jsonify({"message": "Registered successfully"}), 201
    
    return jsonify({"error": "Registration failed"}), 500
   


@app.route('/submit', methods=['POST'])
@utils.measure_this
def submit_data():
    data = request.get_json()  # Parse JSON payload
    return {"received": data}, 200



# Route to add a single domain 
@app.route('/BEadd_domain/<domainName>/<username>',methods=['GET', 'POST'])
@utils.measure_this
def BEadd_new_domain(domainName,username):
    logger.debug(f'New domain is added {domainName}')    
    if user.is_user_exist(username)['message']!="User exist" :        
        return "User is not exist" 
    # Get the domain name from the form data
    logger.debug(f'Domain name is {domainName}')
        
    return domain.add_domain(username,domainName)   


# Route to add a single domain 
@app.route('/',methods=['GET', 'POST'])
@utils.measure_this
def BEadd_new_domain_lc():
        
    return domain.add_domain('dddd','google.com') 
    
# Route to remove a single domain 
@app.route('/BEremove_domain/<domainName>/<username>', methods=['GET', 'POST'])
@utils.measure_this
def remove_domain(domainName,username):
    if user.is_user_exist(username)['message']!="User exist" :
        return "User does not exist" 
    logger.debug(f'Remove domain being called to domain: {domainName}')
    
    logger.debug(f'Domain name is {domainName}')    
    response = domain.remove_domain(username, domainName)

    if response['message'] == "Domain successfully removed":               
        return response       
    return "Error: Domain could not be removed"
   

@app.route('/BEbulk_upload/<filename>/<username>')
@utils.measure_this
def add_from_file(filename,username):    
    if user.is_user_exist(username)['message']!="User exist" :
        return "User does not exist" 

        
    logger.info(f"File for bulk upload:{filename}")
    return domain.add_bulk(username,filename)
    
    
# Route to run Livness check 
# @function.measure_this()

@app.route('/BEcheck/<username>')
@utils.measure_this

def check_livness(username):    
    if user.is_user_exist(username)['message']!="User exist" :
       return "User does not exist"             
    runInfo=check_liveness.livness_check (username)            
    return runInfo
    
    
@app.route('/BEupload', methods=['POST'])
@utils.measure_this
def upload_file():
    if 'file' not in request.files:
        logger.error("No file")
        return {'error': 'No file part provided'}, 400
    
    username = request.form.get('user')
    if not username:
        return {'error': 'No username provided'}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {'error': 'No selected file'}, 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    
    try:
        file.save(filepath)
        add_from_file(filepath, username)
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        return {'message': 'File successfully uploaded', 'file': filepath}
    
    except Exception as e:
        logger.error("Error:", e)
        return {'error': 'An error occurred during file upload'}, 500


def Checkjob(username):    
    globalInfo["runInfo"]=check_liveness.livness_check (username)    
    return  globalInfo["runInfo"]


if __name__ == '__main__':
    app.run(host=app.config['HOST'], port=app.config['BE_PORT'], debug=app.config['FLASK_DEBUG'])
    
