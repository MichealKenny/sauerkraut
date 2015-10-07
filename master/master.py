from bottle import route, run, static_file, request, response, redirect, template
from requests import get, exceptions
import hashlib
import sqlite3


#Connect to database
master_db = sqlite3.connect('master.db', check_same_thread=False)
db = master_db.cursor()


def authorized():
    secret = '05d1ce01dc52e88bf61286994837c82c8fa5089e'
    if request.get_cookie('auth', secret=secret) == 'cabbage':
        return True

    else:
        return False

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
    response.set_cookie('auth', '', secret='admin', expires=0)
    redirect('/login')

@route('/auth', method='POST')
def auth():
    secret = '05d1ce01dc52e88bf61286994837c82c8fa5089e'
    username = request.forms.get('username')
    password = request.forms.get('password')

    #Get data from db.
    try:
        entry = db.execute("SELECT * FROM accounts WHERE username = '{0}'".format(username)).fetchall()[0]

    except IndexError:
        redirect('/login?q=invalid')

    if hashlib.sha512((password + entry[2]).encode('utf-8')).hexdigest() == entry[1]:
        response.set_cookie('auth', 'cabbage', secret=secret, max_age=1000)
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

            page += '<h3><a href="server/{name}">{name}</a> <img src="images/{icon}" title="CPU: {cpu}%, RAM: {ram}%"></h3>'.format(name=server[0], cpu=str(cpu), ram=str(ram), icon=icon)

        except (exceptions.ConnectionError, ValueError):
            page += '<h3><a href="server/{name}">{name}</a> <img src="images/red.png" title="Server down"></h3>'.format(name=server[0])

    return template(html, body=page)

@route('/add')
def add_page():
    if not authorized():
        redirect('/login')

    if request.query.q == 'invalid':
        message = '<font color="red">Invalid Server</font><br/>'
    else:
        message = ''

    return message + open('html/add.html', 'r').read()

@route('/add', method='POST')
def add_server():
    if not authorized():
        redirect('/login')

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

    except exceptions.ConnectTimeout:
        return 'Server down.'


@route('/images/<name>')
def images(name):
    return static_file(name, root='images/')

@route('/css/<name>')
def css(name):
    return static_file(name, root='css/')

run(host='localhost', port=8883)