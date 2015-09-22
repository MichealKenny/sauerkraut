from bottle import route, run, static_file, auth_basic
from requests import get, exceptions


server_db = [
    {'name': 'Slave 1', 'host': 'localhost', 'port': '29547'},
    {'name': 'Slave 2', 'host': 'localhost', 'port': '29548'},
    {'name': 'Slave 3', 'host': 'localhost', 'port': '29549'}]


def login(username, password):
    if username == 'admin' and password == 'admin':
        return True
    else:
        return False

@route('/')
@auth_basic(login)
def index():
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

    return page

@route('/server/<name>')
def server(name):
    return 'Coming soon.'

@route('/images/<name>')
def images(name):
    return static_file(name, root='images/')

run(host='localhost', port=8883)