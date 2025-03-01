from datetime import datetime, timezone
import requests
import concurrent.futures
from queue import Queue
import time
from pythonBE import check_certificate 
from logger.logs import logger
from pythonBE.dbconnection import get_db_connection
from psycopg2 import Error

def livness_check(username):
    # Measure start time
    logger.debug(f'Function "livness_check" is invoked by User- {username}')
    start_date_time = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    start_time = time.time()    
    urls_queue = Queue()
    analyzed_urls_queue = Queue()
    
    # Get domains from database instead of file
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection failed"}
    
    try:
        cursor = connection.cursor()
        
        # Get user_id first
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            return {"message": "User not found"}
        user_id = user_result[0]
        
        # Get domains for this user
        cursor.execute("""
            SELECT d.domain 
            FROM domains d 
            JOIN user_domains ud ON d.id = ud.domain_id 
            WHERE ud.user_id = %s
        """, (user_id,))
        
        domains = cursor.fetchall()
        if not domains:
            return {"message": "No domains found for user"}
            
        for domain in domains:
            urls_queue.put(domain[0])
            
        numberOfDomains = urls_queue.qsize()
        logger.info(f"Total URLs to check: {numberOfDomains}")

        # Define the URL checking function with a timeout and result storage
        def check_url():
            while not urls_queue.empty():
                url = urls_queue.get()
                result = {
                    'domain': url,
                    'status_code': 'FAILED',
                    'ssl_expiration': 'FAILED',
                    'ssl_Issuer': 'FAILED'
                }
                
                try:
                    response = requests.get(f'http://{url}', timeout=10)
                    logger.info(f"URL To Check:{url}")
                    if response.status_code == 200:
                        certInfo = check_certificate.certificate_check(url)
                        result = {
                            'domain': url,
                            'status_code': 'OK',
                            'ssl_expiration': certInfo[0],
                            'ssl_Issuer': certInfo[1][:30]
                        }
                except requests.exceptions.RequestException:
                    pass
                finally:
                    analyzed_urls_queue.put(result)
                    urls_queue.task_done()

        # Update database with results
        def update_results():
            urls_queue.join()  # Wait for all URL checks to finish
            results = []
            
            while not analyzed_urls_queue.empty():
                result = analyzed_urls_queue.get()
                results.append(result)
                
                # Update domain status in database
                cursor.execute("""
                    UPDATE domains 
                    SET status = %s, 
                        ssl_expiration = %s, 
                        ssl_issuer = %s
                    WHERE domain = %s
                """, (
                    result['status_code'],
                    result['ssl_expiration'],
                    result['ssl_Issuer'],
                    result['domain']
                ))
                
                analyzed_urls_queue.task_done()
            
            connection.commit()
            return results

        # Run URL checks in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as liveness_threads_pool:
            futures = [liveness_threads_pool.submit(check_url) for _ in range(100)]
            results = liveness_threads_pool.submit(update_results).result()

        urls_queue.join()

        # Measure end time
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.debug(f"URL liveness check complete in {elapsed_time:.2f} seconds.")

        start_date_time = start_date_time + ' (UTC)'
        return {
            'results': results,
            'start_date_time': start_date_time,
            'numberOfDomains': str(numberOfDomains)
        }

    except Error as e:
        logger.error(f"Database error: {e}")
        return {"message": "Database error occurred"}
    finally:
        if connection:
            cursor.close()
            connection.close()














