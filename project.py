from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash
from flask import make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Electronic, Item, User
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests
from sqlite3 import ProgrammingError
from sqlalchemy.pool import SingletonThreadPool

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "ItemCatalog"


# Connect to Database and create database session
engine = create_engine(
    'sqlite:///catalog_db.db?check_same_thread=False',
    poolclass=SingletonThreadPool)
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius:'
    output += '" 150px;-webkit-border-radius: '
    output += '"150px;-moz-border-radius:150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['user_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        flash("You are now logged out.")
        return redirect(url_for('showElectronic'))
    else:
        # For whatever reason, the given token was invalid.
        flash("You were not logged in")
        return redirect(url_for('showElectronic'))


# JSON APIs to view electronic Information
@app.route('/electronic/<int:electronic_id>/items/JSON')
def ElectronicMenuJSON(electronic_id):
    electronic = session.query(Electronic).filter_by(id=electronic_id).one()
    items = session.query(Item).filter_by(
        electronic_id=electronic_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/electronic/<int:electronic_id>/items/<int:item_id>/JSON')
def ItemJSON(electronic_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(item=item.serialize)


@app.route('/electronic/JSON')
def electronicsJSON():
    electronics = session.query(Electronic).all()
    return jsonify(electronics=[e.serialize for e in electronics])


# Show all electronics
@app.route('/')
@app.route('/electronic/')
def showElectronic():
    electronicsList = session.query(Electronic).all()
    itemList = session.query(Item).order_by(asc(Item.name)).limit(6)
    if 'username' not in login_session:
        return render_template('public_electronics.html',
                               electronics=electronicsList, items=itemList)
    else:
        return render_template('electronics.html',
                               electronics=electronicsList, items=itemList)


# Create a new electronics


@app.route('/electronic/new/', methods=['GET', 'POST'])
def newElectronic():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST' and 'username' in login_session:
        newElectronic = Electronic(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newElectronic)
        flash('New Electronic %s Successfully Created' % newElectronic.name)
        session.commit()
        return redirect(url_for('showElectronic'))
    else:
        return render_template('newElectronic.html')

# Edit a electronics


@app.route('/electronic/<int:electronic_id>/edit/', methods=['GET', 'POST'])
def editElectronic(electronic_id):
    editedElectronic = session.query(
        Electronic).filter_by(id=electronic_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedElectronic.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this electronic catagory. Please create your own catagory in order to edit.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedElectronic.name = request.form['name']
            flash('Electronic Successfully Edited %s' % editedElectronic.name)
            return redirect(url_for('showElectronic'))
    else:
        return render_template('editElectronic.html',
                               electronic=editedElectronic)


# Delete a electronics catagory
@app.route('/electronic/<int:electronic_id>/delete/', methods=['GET', 'POST'])
def deleteElectronic(electronic_id):
    electronicToDelete = session.query(
        Electronic).filter_by(id=electronic_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if electronicToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this electronic catagory. Please create your own catagory in order to delete.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(electronicToDelete)
        flash('%s Successfully Deleted' % electronicToDelete.name)
        session.commit()
        return redirect(url_for('showElectronic', electronic_id=electronic_id))
    else:
        return render_template('deleteElectronic.html',
                               electronic=electronicToDelete)

# Show a electronics menu


@app.route('/electronic/<int:electronic_id>/')
@app.route('/electronic/<int:electronic_id>/items/')
def showItems(electronic_id):

    wantedElectronic = session.query(
        Electronic).filter_by(id=electronic_id).one()
    electronics = session.query(Electronic).all()
    ncreator = getUserInfo(wantedElectronic.user_id)
    itemList = session.query(Item).filter_by(electronic_id=electronic_id).all()
    if 'username' not in login_session or ncreator.id != login_session['user_id']:
        return render_template('publicitems.html', items=itemList,
                               creator=ncreator,
                               electronic=wantedElectronic,
                               electronics=electronics)
    else:
        return render_template('items.html', items=itemList,
                               creator=ncreator,
                               electronic=wantedElectronic,
                               electronics=electronics)


@app.route('/electronic/<int:electronic_id>/<int:item_id>')
@app.route('/electronic/<int:electronic_id>/items/<int:item_id>')
def showOneItem(electronic_id, item_id):
    wantedElectronic = session.query(
        Electronic).filter_by(id=electronic_id).one()
    electronicsList = session.query(Electronic).all()
    item = session.query(Item).filter_by(id=item_id).one()
    creator = getUserInfo(item.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicitem.html', item=item,
                               creator=creator,
                               e=wantedElectronic,
                               electronics=electronicsList)
    else:
        return render_template('item.html', item=item,
                               creator=creator,
                               e=wantedElectronic,
                               electronics=electronicsList)


# Create a new menu item
@app.route('/electronic/<int:electronic_id>/items/new/',
           methods=['GET', 'POST'])
def newItem(electronic_id):
    if 'username' not in login_session:
        return redirect('/login')
    electronic = session.query(Electronic).filter_by(id=electronic_id).one()
    if login_session['user_id'] != electronic.user_id:
        return "<script>function myFunction() {alert('You are not authorized to add items to this electronic catagory. Please create your own catagory in order to add items.');}</script> <body onload='myFunction()''>"
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       description=request.form['description'],
                       price=request.form[
            'price'],
            electronic_id=electronic_id,
            user_id=electronic.user_id)
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showItems', electronic_id=electronic_id))
    else:
        return render_template('newItem.html', electronic_id=electronic_id)

# Edit a menu item


@app.route('/electronic/<int:electronic_id>/items/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editItem(electronic_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one()
    electronic = session.query(Electronic).filter_by(id=electronic_id).one()
    if login_session['user_id'] != electronic.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit menu items to this electronic catagory. Please create your own catagory in order to edit items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showItems', electronic_id=electronic_id))
    else:
        return render_template('edititem.html',
                               electronic_id=electronic_id,
                               item_id=item_id, item=editedItem)


# Delete a menu item
@app.route('/electronic/<int:electronic_id>/items/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(electronic_id, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    electronic = session.query(Electronic).filter_by(id=electronic_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] != electronic.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete menu items to this electronic catagory. Please create your own catagor in order to delete items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showItems', electronic_id=electronic_id))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
