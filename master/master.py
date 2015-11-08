from bottle import ServerAdapter, route, run, static_file, request, response, redirect, template
from multiprocessing.dummy import Pool
from requests import get, post, exceptions, packages
from datetime import datetime
import hashlib, uuid
import sqlite3
import json
import os


def authorized():
    cookie = request.get_cookie('sauerkraut', secret=secret)

    if cookie:
        sk = json.loads(cookie)
        if sk['key'] == key:
            return True

        else:
            return False

    else:
        return False

def admin():
    entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(current_user())).fetchall()[0]

    if entry[3] == 'admin':
        return True

    else:
        return False

def current_user():
    sk = json.loads(request.get_cookie('sauerkraut', secret=secret))

    return sk['username']


def create_hash(password, salt=uuid.uuid4().hex):

    hash_pass = hashlib.sha512((password + salt).encode('utf-8')).hexdigest()

    return hash_pass, salt


def get_server_status(server):
    global green
    global yellow
    global red

    try:
        health = get('https://{host}:{port}/status'.format(host=server[1], port=server[2]), timeout=0.4, verify=False).json()
        cpu = health['cpu']
        ram = health['ram']

        if cpu > 85 or ram > 85:
            icon = 'yellow.png'
            yellow += 1
        else:
            icon = 'green.png'
            green += 1

        row = '<tr><td><a href="server?server={name}">{name}</a></td><td>{host}:{port}</td><td>{cpu}%</td><td>{ram}' \
              '%</td><td><img src="images/{icon}"></td><td><a href="remove-server?server={name}">X</a></td></tr>'\
            .format(name=server[0], host=server[1], port=server[2], cpu=str(cpu), ram=str(ram), icon=icon)

        return row

    except (exceptions.RequestException, ValueError):
        row = '<tr><td><a href="server?server={name}">{name}</a></td><td>{host}:{port}</td><td>N/A</td><td>N/A' \
              '</td><td><img src="images/red.png"></td><td><a href="remove-server?server={name}">X</a></td></tr>'\
            .format(name=server[0], host=server[1], port=server[2])
        red += 1

        return row

    except KeyError:
        row = '<tr><td><a href="server?server={name}">{name}</a></td><td>{host}:{port}</td><td>N/A</td><td>N/A' \
              '</td><td>Not Auth</td><td><a href="remove-server?server={name}">X</a></td></tr>'\
            .format(name=server[0], host=server[1], port=server[2])
        red += 1

        return row



@route('/login')
def login():
    if authorized():
        redirect(url + '/')


    return open('html/login.html', 'r').read()


@route('/logout')
def logout():
    log.execute("INSERT INTO events VALUES ('User {0} logged out','Logout','{0}','{1}')"
        .format(current_user(), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
    logs_db.commit()

    response.set_cookie('sauerkraut', '', secret=secret, expires=0)
    redirect(url + '/login')


@route('/auth', method='POST')
def auth():
    username = request.forms.get('username').lower()
    password = request.forms.get('password')

    #Get data from db.
    try:
        entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(username)).fetchall()[0]

    except IndexError:
        log.execute("INSERT INTO events VALUES ('User {0} attempted to login from {2}','Invalid Login','{0}','{1}')"
                    .format(username, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), request.remote_addr))

        redirect(url + '/login#invalid-login')

    if create_hash(password, entry[2])[0] == entry[1]:
        data = json.dumps({'username': username, 'key': key})
        response.set_cookie(name='sauerkraut', value=data, secret=secret, secure=True)

        last = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        db.execute("UPDATE accounts SET last='{0}' WHERE username='{1}'".format(last, username))
        master_db.commit()

        log.execute("INSERT INTO events VALUES ('User {0} logged in from {2}','Login','{0}','{1}')"
                    .format(username, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), request.remote_addr))
        logs_db.commit()

        if (username, password) == ('admin', 'admin'):
            redirect(url + '/manage/change-password#default-admin')
            
        else:
            redirect(url + '/')

    else:
        log.execute("INSERT INTO events VALUES ('User {0} attempted to login from {2}','Invalid Login','{0}','{1}')"
                    .format(username, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), request.remote_addr))
        redirect(url + '/login#invalid-login')


@route('/')
def index():
    global green
    global yellow
    global red

    if not authorized():
        redirect(url + '/login')

    html = open('html/list.html', 'r').read()

    servers = db.execute('SELECT * FROM servers').fetchall()
    if len(servers) == 0:
        redirect(url + '/add#no-servers')

    else:
        green = 0
        yellow = 0
        red = 0

        pool = Pool(len(servers))
        page = pool.map(get_server_status, servers)
        pool.close()

    return template(html, {'body': ''.join(page), 'username':current_user(), 'green': green, 'yellow': yellow, 'red': red})


@route('/add')
def add_page():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    html = open('html/add.html', 'r').read()
    return template(html, username=current_user())


@route('/add', method='POST')
def add_server():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    name = request.forms.get('name').lower()
    host = request.forms.get('host')
    port = request.forms.get('port')
    validate = request.forms.get('validate')

    if validate:
        try:
            get('https://{host}:{port}/status'.format(host=host, port=port), verify=False)

        except:
            redirect(url + '/add#invalid-server')

    if len(name) < 4:
        redirect(url + '/add#invalid-name')

    if set('[ ~!#$@%^&*()+{}":;\']+$').intersection(name):
        redirect(url + '/add#invalid-name')

    exists = db.execute("SELECT name FROM servers WHERE name = '{0}'".format(name)).fetchall()
    if exists:
        redirect(url + '/add#name-exists')

    #Add server to databases.
    db.execute("INSERT INTO servers VALUES ('{0}','{1}','{2}')".format(name, host, port))
    master_db.commit()

    log.execute("INSERT INTO events VALUES ('Server {0} added','Server Added','{1}','{2}')"
                .format(name, current_user(), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
    logs_db.commit()

    redirect(url + '/')


@route('/remove-server')
def remove_server():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    db.execute("DELETE FROM servers WHERE name = '{0}'".format(request.query.server))
    master_db.commit()

    log.execute("INSERT INTO events VALUES ('Server {0} removed','Server Removed','{1}','{2}')"
                .format(request.query.server, current_user(), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
    log.execute("DELETE FROM servers WHERE name = '{0}'".format(request.query.server))
    logs_db.commit()

    redirect(url + '/')


@route('/server')
def server():
    if not authorized():
        redirect(url + '/login')

    name = request.query.server
    interval = request.query.plots or 120

    try:
        html = open('html/server.html', 'r').read()

        labels, cpu_data, ram_data, disk_data, disk_read_data, \
        disk_write_data, total_packets_data = '[', '[', '[', '[', '[', '[', '['
        cpu_total, ram_total, disk_total, disk_read_total, \
        disk_write_total, total_packets_total = 0, 0, 0, 0, 0, 0

        count = 0
        avg_count = 0


        data = log.execute("SELECT * FROM servers WHERE name = '{0}'".format(name)).fetchall()
        data = data[-int(interval):]
        for row in data:
            cpu_total += float(row[2])
            ram_total += float(row[3])
            disk_total += float(row[4])
            disk_read_total += float(row[5])
            disk_write_total += float(row[6])
            total_packets_total += float(row[7])

            count += 1
            avg_count += 1

            avg = len(data) / 9

            if count > avg:
                labels += '"' + row[0][-8:] + '",'
                cpu_data += '"' + str(round(cpu_total/avg_count, 2)) + '",'
                ram_data += '"' + str(round(ram_total/avg_count, 2)) + '",'
                disk_data += '"' + str(round(disk_total/avg_count, 2)) + '",'
                disk_read_data += '"' + str(round(disk_read_total/avg_count, 2)) + '",'
                disk_write_data += '"' + str(round(disk_write_total/avg_count, 2)) + '",'
                total_packets_data += '"' + str(round(total_packets_total/avg_count, 2)) + '",'

                count = 0


        labels = labels[:-1] + ']'
        cpu_data = cpu_data[:-1] + ']'
        ram_data = ram_data[:-1] + ']'
        disk_data = disk_data[:-1] + ']'
        disk_read_data = disk_read_data[:-1] + ']'
        disk_write_data = disk_write_data[:-1] + ']'
        total_packets_data = total_packets_data[:-1] + ']'

        return template(html, {'name': name, 'username': current_user(), 'labels': labels, 'cpu_data': cpu_data,
                               'ram_data': ram_data, 'disk_data': disk_data, 'disk_read_data': disk_read_data,
                               'disk_write_data': disk_write_data, 'total_packets_data': total_packets_data})

    except exceptions.RequestException:
        return 'Server down.'


@route('/manage')
def manage():
    if not authorized():
        redirect(url + '/login')

    table = ''

    for entry in db.execute("SELECT * FROM accounts"):
        table += '<tr><td>{name}</td><td>{perms}</td><td>{last}</td><td><a href="remove-user?username={name}">X</a>' \
                 '</td></tr>'.format(name=entry[0], perms=entry[3], last=entry[4])

    html = open('html/manage.html', 'r').read()
    return template(html, username=current_user(), table=table)

@route('/manage/change-password')
def change_password_page():
    if not authorized():
        redirect(url + '/login')

    return template(open('html/change-password.html', 'r').read(), username=current_user())

@route('/manage/change-password', method='POST')
def change_password():
    if not authorized():
        redirect(url + '/login')

    old_pass = request.forms.get('old-password')
    new_pass = request.forms.get('new-password')
    new_pass_confirm = request.forms.get('new-password-confirm')

    if new_pass == new_pass_confirm:
        entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(current_user())).fetchall()[0]
        if create_hash(old_pass, entry[2])[0] == entry[1]:
            new_hash, new_salt = create_hash(new_pass)

            db.execute("UPDATE accounts SET hash='{0}', salt='{1}' WHERE username='{2}'".format(new_hash, new_salt, current_user()))
            master_db.commit()

            log.execute("INSERT INTO events VALUES ('Password changed for: {0}','Password Change','{0}','{1}')"
                .format(current_user(), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
            logs_db.commit()

            redirect(url + '/logout')

        else:
            redirect(url + '/manage/change-password#invalid-old-pass')

    else:
        redirect(url + '/manage/change-password#invalid-new-pass')


@route('/manage/new-user')
def new_user_page():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    html = open('html/new-user.html', 'r').read()
    return template(html, username=current_user())


@route('/manage/new-user', method='POST')
def new_user():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    username = request.forms.get('username').lower()
    password = request.forms.get('password')
    password_confirm = request.forms.get('password-confirm')
    perms = request.forms.get('perms')

    if password == password_confirm:
        if len(password) < 8:
            redirect(url + '/manage/new-user#pass-length')

        if len(username) < 4:
            redirect(url + '/manage/new-user#invalid-username')

        if set('[ ~!#$@%^&*()+{}":;\']+$').intersection(username):
            redirect(url + '/manage/new-user#invalid-username')

        exists = db.execute("SELECT username FROM accounts WHERE username = '{0}'".format(username)).fetchall()
        if exists:
            redirect(url + '/manage/new-user#username-taken')



        hash, salt = create_hash(password)
        db.execute("INSERT INTO accounts VALUES ('{0}', '{1}', '{2}', '{3}', 'Never')".format(username, hash, salt, perms))
        master_db.commit()

        log.execute("INSERT INTO events VALUES ('User {0} added','User Added','{1}','{2}')"
                    .format(username, current_user(), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
        logs_db.commit()

        redirect(url + '/manage')

    else:
        redirect(url + '/manage/new-user#pass-invalid')


@route('/remove-user')
def remove_user():
    if not authorized():
        redirect(url + '/login')

    user = request.query.username

    if user == 'admin':
        redirect(url + '/denied')

    if current_user() != user:
        if not admin():
            redirect(url + '/denied')

    db.execute("DELETE FROM accounts WHERE username = '{0}'".format(user))
    master_db.commit()

    log.execute("INSERT INTO events VALUES ('User {0} removed','User Removed','{1}','{2}')"
                .format(user, current_user(), datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
    logs_db.commit()

    if current_user() == user:
        redirect(url + '/logout')

    else:
        redirect(url + '/manage')

@route('/denied')
def denied():
    response.status = 401
    return '<h2>401 Unauthorized</h2><p>You lack the required permission to perform this action<p>'


@route('/manage/event-viewer')
def event_viewer():
    if not authorized():
        redirect(url + '/login')

    html = open('html/event-viewer.html', 'r').read()
    page = ''

    events = log.execute('SELECT * FROM events').fetchall()
    for event in reversed(events):
        page += '<tr><td>{0}</a></td><td>{1}</td><td>{2}</td><td>{3}</td></tr>'\
            .format(event[0], event[1], event[2], event[3])

    return template(html, body=page, username=current_user())


@route('/quick-config')
def quick_config():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    html = open('html/quick-config.html', 'r').read()
    return template(html, username=current_user())


@route('/custom-config')
def custom_config():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    html = open('html/custom-config.html', 'r').read()
    options = ''

    servers = db.execute('SELECT * FROM servers').fetchall()

    for server in servers:
        options += '<option value="{name}">{name}</option>'.format(name=server[0])

    return template(html, options=options, username=current_user(), output='', output_box_css='')


@route('/custom-config', method='POST')
def custom_config_execute():
    if not authorized():
        redirect(url + '/login')

    if not admin():
        redirect(url + '/denied')

    type = request.forms.get('type')
    payload = {'command': request.forms.get('command'),
               'path': request.forms.get('path'),
               'type': type}

    output = {}
    return_output = request.forms.get('output')

    for server in request.forms.getall('selection'):
        server_info = db.execute("SELECT * FROM servers WHERE name='{0}'".format(server)).fetchall()[0]
        address = 'https://{0}:{1}/execute'.format(server_info[1], server_info[2])
        req = post(address, data=payload, verify=False)
        output[server] = req.json()['output']

    page = ''
    output_box_css = ''

    if return_output and type == 'non-blocking':
        output_box_css = 'border: 1px solid gray;padding-left: 25px;'
        for item in output:
            page += '<h4>{0}</h4><p style="font-size: 10px;">{1}</p>'.format(item, output[item].replace('\n', '<br>'))

    html = open('html/custom-config.html', 'r').read()
    options = ''

    servers = db.execute('SELECT * FROM servers').fetchall()

    for server in servers:
        options += '<option value="{name}">{name}</option>'.format(name=server[0])

    return template(html, options=options, username=current_user(), output=page,
                    output_box_css=output_box_css)




@route('/images/<name>')
def images(name):
    return static_file(name, root='images/')


@route('/css/<name>')
def css(name):
    return static_file(name, root='css/', mimetype='text/css')


@route('/js/<name>')
def js(name):
    return static_file(name, root='js/', mimetype='text/javascript')


class SSLWSGIRefServer(ServerAdapter):
    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        import ssl
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.socket = ssl.wrap_socket (
         srv.socket,
         certfile='master.pem',  # path to certificate
         server_side=True)
        srv.serve_forever()


if __name__ == '__main__':
    print('Sauerkraut - Cluster Administration Tool')

    if not os.path.isdir('dbs'):
        os.mkdir('dbs')

    if not os.path.isfile('master.pem'):
        try:
            os.system("openssl req -new -x509 -keyout master.pem -out master.pem -days"
                      " 365 -nodes -subj '/C=IE/ST=Connaught/L=Galway/CN=Sauerkraut'")

            print('Generated master.pem x509 certificate')

        except:
            print('Sauerkraut requires an x509 openssl generated master.pem file, could not auto generate.')
            print('Generate with: openssl req -new -x509 -keyout master.pem -out master.pem -days 365 -nodes')
            quit()

    if not os.path.isfile('config.json'):
        print('========================================\n\nFresh Install, Please fill in the following details:\n')

        config = json.dumps({'secret': '05d1ce01dc52e88bf61286994837c82c8fa5089e', 'key': 'cabbage',
                             'host': input('Host: '), 'url': input('URL: '),
                             'port': int(input('Port: '))}, indent=4)

        config_file = open('config.json', 'w+')
        config_file.write(config)
        config_file.close()

        print('\nCreated configuration file, it can be changed at any time.')

    if not os.path.isfile('dbs/master.db'):
        #Connect to database
        master_db = sqlite3.connect('dbs/master.db', check_same_thread=False)
        db = master_db.cursor()

        db.execute("CREATE TABLE servers (name text, host text, port text)")
        db.execute("CREATE TABLE accounts (username text, hash text, salt text, perms text, last text)")
        db.execute("INSERT INTO accounts VALUES ('admin','33ff7d10cd1f5bc60c0d5d0a331f39a1c4ad98ed5bc2e357f291700197"
                                                         "c38734f3da4e9a7bf421b4cad90fcb5a3c38171493f306af24c8acc733"
                                                         "20c3339e09aa','230f3cbd511a4ac79dff00a998dd6641',"
                                                         "'admin', 'Never')")
        master_db.commit()
        master_db.close()

        print('Created master database, default login is admin:admin')

    if not os.path.isfile('dbs/logs.db'):
        #Connect to database
        logs_db = sqlite3.connect('dbs/logs.db', check_same_thread=False)
        log = logs_db.cursor()

        log.execute("CREATE TABLE events (event text, type text, user text, time text)")
        log.execute("CREATE TABLE servers (time text, name text, cpu text, ram text, "
                    "disk_usage text, disk_read text,disk_write text, total_packets text)")

        logs_db.commit()
        logs_db.close()

        print('Created logs database')


    #Connect to databases
    master_db = sqlite3.connect('dbs/master.db', check_same_thread=False)
    db = master_db.cursor()

    logs_db = sqlite3.connect('dbs/logs.db', check_same_thread=False)
    log = logs_db.cursor()

    config_file = open('config.json', 'r')
    config = json.loads(config_file.read())
    config_file.close()

    secret = config['secret']
    key = config['key']
    host = config['host']
    port = config['port']
    ext = config['url']

    url = 'https://{0}:{1}'.format(ext, str(port))

    print('https://{0}:{1}/'.format(host, port))
    srv = SSLWSGIRefServer(host=host, port=port)
    packages.urllib3.disable_warnings()
    run(server=srv)