from bottle import route, run, static_file, request, response, redirect, template
from requests import get, exceptions
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
    entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(username())).fetchall()[0]

    if entry[3] == 'admin':
        return True

    else:
        return False

def username():
    sk = json.loads(request.get_cookie('sauerkraut', secret=secret))

    return sk['username']


def create_hash(password, salt=uuid.uuid4().hex):

    hash_pass = hashlib.sha512((password + salt).encode('utf-8')).hexdigest()

    return hash_pass, salt


@route('/login')
def login():
    if authorized():
        redirect('/')

    if request.query.q == 'invalid':
        message = '<font color="red">Invalid Login</font><br/>'
    else:
        message = ''

    return message + open('html/login.html', 'r').read()


@route('/logout')
def logout():
    response.set_cookie('sauerkraut', '', secret=secret, expires=0)
    redirect('/login')


@route('/auth', method='POST')
def auth():
    username = request.forms.get('username')
    password = request.forms.get('password')

    #Get data from db.
    try:
        entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(username)).fetchall()[0]

    except IndexError:
        redirect('/login?q=invalid')

    if create_hash(password, entry[2])[0] == entry[1]:
        data = json.dumps({'username': username, 'key': key})
        response.set_cookie(name='sauerkraut', value=data, secret=secret, max_age=1000)

        if password == 'admin':
            redirect('/manage/change-password')
            
        else:
            redirect('/')

    else:
        redirect('/login?q=invalid')


@route('/')
def index():
    if not authorized():
        redirect('/login')

    page = ''
    html = open('html/list.html', 'r').read()

    for server in db.execute("SELECT * FROM servers"):
        try:
            health = get('http://{host}:{port}/status'.format(host=server[1], port=server[2]), timeout=0.01).json()
            cpu = health['cpu']
            ram = health['ram']

            if cpu > 85 or ram > 85:
                icon = 'yellow.png'
            else:
                icon = 'green.png'

            page += '<tr><td><a href="server/{name}">{name}</a></td><td>{host}:{port}</td><td>{cpu}%</td><td>{ram}%</td><td><img src="images/{icon}"></td><td><a href="remove?server={name}">X</a></td></tr>'.format(name=server[0], host=server[1], port=server[2], cpu=str(cpu), ram=str(ram), icon=icon)

        except (exceptions.RequestException, ValueError):
            page += '<tr><td><a href="server/{name}">{name}</a></td><td>{host}:{port}</td><td>N/A</td><td>N/A</td><td><img src="images/red.png"></td><td><a href="remove?server={name}">X</a></td></tr>'.format(name=server[0], host=server[1], port=server[2])

    return template(html, body=page, username=username())


@route('/add')
def add_page():
    if not authorized():
        redirect('/login')

    if not admin():
        redirect('/denied')

    if request.query.q == 'invalid':
        message = '<font color="red">Invalid Server</font><br/>'
    else:
        message = ''

    return message + open('html/add.html', 'r').read()


@route('/add', method='POST')
def add_server():
    if not authorized():
        redirect('/login')

    if not admin():
        redirect('/denied')

    name = request.forms.get('name')
    host = request.forms.get('host')
    port = request.forms.get('port')

    try:
        get('http://{host}:{port}/status'.format(host=host, port=port))

    except:
        redirect('/add?q=invalid')

    #Add server to database.
    db.execute("INSERT INTO servers VALUES ('{0}','{1}','{2}')".format(name, host, port))
    master_db.commit()

    redirect('/')


@route('/remove')
def remove_server():
    if not authorized():
        redirect('/login')

    if not admin():
        redirect('/denied')

    db.execute("DELETE FROM servers WHERE name = '{0}'".format(request.query.server))
    master_db.commit()

    redirect('/')


@route('/server/<name>')
def server(name):
    if not authorized():
        redirect('/login')


    entry = db.execute("SELECT * FROM servers WHERE name = '{0}'".format(name)).fetchall()[0]

    try:
        health = get('http://{host}:{port}/status'.format(host=entry[1], port=entry[2]), timeout=0.1).json()
        cpu = health['cpu']
        ram = health['ram']


        html = open('html/server.html', 'r').read()
        return template(html, {'name': name, 'cpu': cpu, 'ram': ram})

    except exceptions.RequestException:
        return 'Server down.'


@route('/manage/change-password')
def change_password_page():
    if not authorized():
        redirect('/login')

    return template(open('html/change-password.html', 'r').read(), username=username())

@route('/manage/change-password', method='POST')
def change_password():
    if not authorized():
        redirect('/login')

    old_pass = request.forms.get('old-password')
    new_pass = request.forms.get('new-password')
    new_pass_confirm = request.forms.get('new-password-confirm')

    if new_pass == new_pass_confirm:
        entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(username())).fetchall()[0]
        if create_hash(old_pass, entry[2])[0] == entry[1]:
            new_hash, new_salt = create_hash(new_pass)

            db.execute("UPDATE accounts SET hash='{0}', salt='{1}' WHERE username='{2}'".format(new_hash, new_salt, username()))
            master_db.commit()

            redirect('/logout')

        else:
            redirect('/manage/change-password?q=invalid-old-pass')

    else:
        redirect('/manage/change-password?q=invalid-new-pass')


@route('/manage/new-user')
def new_user_page():
    if not authorized():
        redirect('/login')

    if not admin():
        redirect('/denied')

    return open('html/new-user.html', 'r').read()


@route('/manage/new-user', method='POST')
def new_user():
    if not authorized():
        redirect('/login')

    if not admin():
        redirect('/denied')

    username = request.forms.get('username')
    password = request.forms.get('password')
    password_confirm = request.forms.get('password-confirm')
    perms = request.forms.get('perms')
    if password == password_confirm:
        hash, salt = create_hash(password)
        db.execute("INSERT INTO accounts VALUES ('{0}', '{1}', '{2}', '{3}')".format(username, hash, salt, perms))
        master_db.commit()

        redirect('/')

    else:
        redirect('/manage/new-user?q=pass-invalid')


@route('/denied')
def denied():
    return 'You lack the required permission to perform this action'


@route('/images/<name>')
def images(name):
    return static_file(name, root='images/')


@route('/css/<name>')
def css(name):
    return static_file(name, root='css/', mimetype='text/css')


@route('/js/<name>')
def js(name):
    return static_file(name, root='js/', mimetype='text/javascript')


if __name__ == '__main__':
    print('Sauerkraut - Cluster Administration Tool')
    if not os.path.isfile('config.json'):
        print('========================================\n\nFresh Install, Please fill in the following details:\n')

        config = json.dumps({'secret': '05d1ce01dc52e88bf61286994837c82c8fa5089e', 'key': 'cabbage',
                             'host': input('Host: '), 'port': int(input('Port: '))}, indent=4)

        config_file = open('config.json', 'w+')
        config_file.write(config)
        config_file.close()

        print('\nCreated configuration file, it can be changed at any time.')

    if not os.path.isfile('master.db'):
        #Connect to database
        master_db = sqlite3.connect('master.db', check_same_thread=False)
        db = master_db.cursor()

        db.execute("CREATE TABLE servers (name text, host text, port text)")
        db.execute("CREATE TABLE accounts (username text, hash text, salt text, perms text)")
        db.execute("INSERT INTO accounts VALUES ('admin','33ff7d10cd1f5bc60c0d5d0a331f39a1c4ad98ed5bc2e357f291700197"
                                                         "c38734f3da4e9a7bf421b4cad90fcb5a3c38171493f306af24c8acc733"
                                                         "20c3339e09aa','230f3cbd511a4ac79dff00a998dd6641', 'admin')")
        master_db.commit()
        master_db.close()

        print('Created database, default login is admin:admin')

    #Connect to database
    master_db = sqlite3.connect('master.db', check_same_thread=False)
    db = master_db.cursor()

    config_file = open('config.json', 'r')
    config = json.loads(config_file.read())
    config_file.close()

    secret = config['secret']
    key = config['key']
    host = config['host']
    port = config['port']

    run(host=host, port=port)