from bottle import route, run, static_file, request, response, redirect
from requests import get, exceptions


server_db = [
    {'name': 'Slave 1', 'host': 'localhost', 'port': '29547'},
    {'name': 'Slave 2', 'host': 'localhost', 'port': '29548'},
    {'name': 'Slave 3', 'host': 'localhost', 'port': '29549'}]


@route('/login')
def login():
    if request.get_cookie('auth', secret='admin') == 'admin':
        redirect('/')

    return open('html/login.html', 'r').read()

@route('/logout')
def login():
    response.set_cookie('auth', '', secret='admin', expires=0)
    redirect('/')

@route('/auth', method='POST')
def auth():
    username = request.forms.get('username')
    password = request.forms.get('password')
    if username == 'admin' and password == 'admin':
        response.set_cookie('auth', 'admin', secret='admin', max_age=1000)
        redirect('/')
    else:
        redirect('/login')


@route('/')
def index():
    if request.get_cookie('auth', secret='admin') != 'admin':
        redirect('/login')

    page = '<img src="images/header.png">'

    for server in server_db:
        try:
            health = get('http://{host}:{port}/status'.format(host=server['host'], port=server['port']), timeout=0.1).json()
            cpu = health['cpu']
            ram = health['ram']

            if cpu > 85 or ram > 85:
                icon = 'yellow.png'
            else:
                icon = 'green.png'

            page += '<h3><a href="server/{name}">{name}</a> <img src="images/{icon}" title="CPU: {cpu}%, RAM: {ram}%"></h3>'.format(name=server['name'], cpu=str(cpu), ram=str(ram), icon=icon)

        except exceptions.ConnectionError:
            page += '<h3><a href="server/{name}">{name}</a> <img src="images/red.png" title="Server down"></h3>'.format(name=server['name'])

    return page + '<a href="/logout">Logout</a>'

@route('/server/<name>')
def server(name):
    return 'Coming soon.'

@route('/images/<name>')
def images(name):
    return static_file(name, root='images/')

@route('/css/<name>')
def images(name):
    return static_file(name, root='css/')

run(host='localhost', port=8883)