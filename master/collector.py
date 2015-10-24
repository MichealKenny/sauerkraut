from datetime import datetime
from requests import get
from time import sleep
import sqlite3

master_db = sqlite3.connect('dbs/master.db', check_same_thread=False)
db = master_db.cursor()

logs_db = sqlite3.connect('dbs/logs.db', check_same_thread=False)
log = logs_db.cursor()


def trim_logs(length):
    log.execute("DELETE FROM servers WHERE ROWID IN (SELECT ROWID FROM servers ORDER BY"
                " ROWID DESC LIMIT -1 OFFSET {0})".format(length))

    log.execute("DELETE FROM events WHERE ROWID IN (SELECT ROWID FROM "
                "events ORDER BY ROWID DESC LIMIT -1 OFFSET 2500)")

print('Collecting..')
while True:

    servers = db.execute("SELECT * FROM servers").fetchall()
    for server in servers:
        try:
            health = get('https://{host}:{port}/extended'.format(host=server[1], port=server[2]), timeout=0.1, verify=False).json()

        except:
            health = {'cpu': 0, 'ram': 0, 'disk_usage': 0, 'disk_read': 0, 'disk_write': 0, 'total_packets': 0}

        log.execute("INSERT INTO servers VALUES ('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}')"
                    .format(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                            server[0], health['cpu'], health['ram'], health['disk_usage'],
                            health['disk_read'], health['disk_write'], health['total_packets']))

    trim_logs(int(len(servers)) * 120)
    logs_db.commit()
    sleep(5)

