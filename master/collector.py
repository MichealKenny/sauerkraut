from datetime import datetime
from requests import get, packages
from multiprocessing.dummy import Pool
from time import sleep
import sqlite3


def trim_logs(length):
    """
    Trim the oldest entries from the database.

    :param length: Max length of the database.
    :return: Nothing.
    """

    log.execute("DELETE FROM servers WHERE ROWID IN (SELECT ROWID FROM servers ORDER BY"
                " ROWID DESC LIMIT -1 OFFSET {0})".format(length))

    log.execute("DELETE FROM events WHERE ROWID IN (SELECT ROWID FROM "
                "events ORDER BY ROWID DESC LIMIT -1 OFFSET 2500)")


def get_server_status(server):
    """
    Check the /extended endpoint of the given server and return the data.

    :param server: List of data on the given server.
    :return: Server name, and a dictonary of the server health.
    """

    try:
        health = get('https://{host}:{port}/extended'.format(host=server[1], port=server[2]), timeout=0.4, verify=False).json()

    except:
        health = {'cpu': 0, 'ram': 0, 'disk_usage': 0, 'disk_read': 0, 'disk_write': 0, 'total_packets': 0}

    return server[0], health


if __name__ == '__main__':
    try:
        packages.urllib3.disable_warnings()

    except:
        pass

    master_db = sqlite3.connect('dbs/master.db', check_same_thread=False)
    db = master_db.cursor()

    logs_db = sqlite3.connect('dbs/logs.db', check_same_thread=False)
    log = logs_db.cursor()

    print('Collecting..')
    while True:
        servers = db.execute("SELECT * FROM servers").fetchall()
        if len(servers) == 0:
            processes = 1
        
        else:
            processes = len(servers)

        pool = Pool(processes)
        statuses = pool.map(get_server_status, servers)
        pool.close()

        for status in statuses:
            health = status[1]
            log.execute("INSERT INTO servers VALUES ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')".format(
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), status[0], health['cpu'], health['ram'],
                health['disk_usage'],health['disk_read'], health['disk_write'], health['total_packets']))


        trim_logs(int(len(servers)) * 17000)

        committed = False

        while not committed:
            try:
                logs_db.commit()
                committed = True

            except:
                sleep(0.3)

        sleep(5)

