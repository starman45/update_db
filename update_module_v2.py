import requests
import json
import argparse
import os
import getpass
import time
import http.cookiejar
from typing import NamedTuple
from datetime import timedelta


class Args(NamedTuple):
    """ Command-line arguments """
    url: str


def get_args() -> Args:

    """ Get command-line arguments """

    parser = argparse.ArgumentParser(
        description='Script for Update modules and verification that updates are completed successfully',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)


    parser.add_argument('url',
                        metavar='url',
                        help='url of the service')

    args = parser.parse_args()


    return Args(args.url)


def get_list_db(url):
    action_url = "http://{}/web/database/list".format(url)
    data = {"params": {}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(action_url, data=json.dumps(data), headers=headers)
        db = response.json()
    except Exception as e:
        print("URL:", url)
        print("Connection establishment failed!")
        print(e)
        print("------------------------------")
        db = {"error": e}

    return db


def get_list_db_availability(url):
    action_url = "http://{}/jsonrpc".format(url)
    data = {"jsonrpc":"2.0","method":"call","params":{"method":"list","service":"db","args":{}}}
    headers = {"Content-Type": "application/json"}
    jar = http.cookiejar.FileCookieJar('/tmp/cookies')

    try:
        response = requests.post(action_url, data=json.dumps(data), headers=headers, cookies=jar)
        db = response.json()
    except Exception as e:
        print("URL:", url)
        print("Connection establishment failed!")
        print(e)
        print("------------------------------")
        db = {"error": e}

    return db


def main() -> None:

    args = get_args()
    url = args.url

    list_of_existing_databases = get_list_db(f"{url}").get('result')
    current_user = getpass.getuser()
    file_route = "/home/{0}/verification_script/updatelogs.logs".format(current_user)

    errors = 0
    update_status = ""
    fail_db_updates = []
    time_taken_to_update_db = 0


    if not os.path.exists(file_route):
        os.system("mkdir /home/{0}/verification_script && touch {1}".format(current_user, file_route))


    '''
        Updating list of modules of the existing databases in the url given
    '''
    for database in list_of_existing_databases:

        try:

            start_time = time.time()
            cmd = "python odoo-bin -c /etc/odoo/odoo.conf -d {0} -u all --xmlrpc-port=8569 --stop-after-init --logfile={1} && echo SUCCESS db:{0} >> {1} || echo FAIL db:{0} >> {1}".format(database, file_route)

            os.system(cmd)

            time_taken_to_update_db = (time.time() - start_time)//1


            with open(file_route,"r") as given_file:
                for line in given_file:
                    if "CRITICAL"  in line:
                        errors += 1
                        print(line)
                    elif "ERROR"  in line:
                        print(line)
                    elif "FAIL" in line:
                        update_status = "FAIL"
                        print(line + "time_taken_to_update_database (hh:mm:ss) --> "+ str(timedelta(seconds=time_taken_to_update_db)))
                        print("-"*20,"\n")
                        fail_db_updates.append(database)
                    elif "SUCCESS" in line:
                        print(line + "time_taken_to_update_database (hh:mm:ss) --> "+ str(timedelta(seconds=time_taken_to_update_db)))
                        print("-"*20,"\n")

            with open(file_route,"w") as given_file:
                given_file.write("")


        except Exception as e:
            print(e)


    if errors > 0 or update_status =="FAIL":
        print()
        print(f"Error al actualizar lista de modulos en las bases de datos --> {fail_db_updates}")
    else:
        print("Sin errores al actualizar lista de modulos")



    '''
        Verifying the service is up and working
    '''

    health_check_databases = []
    unhealth_check_databases = []

    list_of_available_databases = get_list_db_availability(url).get('result')

    for database in list_of_available_databases:
        if database in list_of_existing_databases:
            health_check_databases.append(database)
        else:
            unhealth_check_databases.append(database)


    print("\nBases de datos con el servicio disponible --> ",health_check_databases, "\n")

    print("\nBases de datos con el servicio no disponible --> ",unhealth_check_databases, "\n")




# --------------------------------------------------
if __name__ == '__main__':
    main()
