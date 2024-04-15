from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from flask import session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
client = MongoClient('mongodb://localhost:27017/')
db = client['mt1'] 
users_collection = db['users']
events_collection = db['events'] 
participations_collection = db['participations']

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('display_all'))
        else:
            return render_template('login.html', message='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        
        password_hash = generate_password_hash(password)
        if users_collection.find_one({'username': username}):
            return render_template('register.html', message='Username already exists')
        else:
            users_collection.insert_one({'username': username, 'password': password_hash, 'email': email , 'phone': phone})
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/host',methods=['GET', 'POST'])
def host():
    if request.method == 'POST':
        event_title = request.form['title']
        if events_collection.find_one({'title': event_title}):
            return render_template('host.html', message='Event title already exists. Please choose a different title.')
        event_data = {
            'title': event_title,
            'venue': request.form['venue'],
            'limit': request.form.get('limit', type=int),
            'date': request.form['date'],
            'time': request.form['time'],
            'description': request.form['description'],
            'participants': 0,
            'host': session['username'],
            'has_attended': False,  # Set default value to False
        }
        events_collection.insert_one(event_data)
        return redirect(url_for('host'))
    else:
        return render_template('host.html')

@app.route('/all')
def display_all():
    all_events_cursor = events_collection.find()
    today = datetime.today()

    all_events = list(all_events_cursor)

    for event in all_events:
        event['date'] = datetime.strptime(event['date'], '%Y-%m-%d')

        if 'username' in session:
            username = session['username']
            # Check if the user has already attended this event
            participation = participations_collection.find_one({'username': username, 'event_title': event['title']})
            if participation:
                event['has_attended'] = True
            else:
                event['has_attended'] = False
        else:
            event['has_attended'] = False

    return render_template('all.html', events=all_events, today=today)


@app.route('/event/<event_title>')
def event_details(event_title):
    event = events_collection.find_one({'title': event_title})

    if event:
        return render_template('event_details.html', event=event)
    else:
        return "Event not found", 404

@app.route('/attend')
def attend_event():
    event_title = request.args.get('event_title')

    if not event_title:
        return "Error: No event title provided."

    username = session.get('username')

    if not username:
        return render_template('participated.html', events=[])

    event = events_collection.find_one({'title': event_title, 'host': username})
    if event:
        return redirect(url_for('display_all'))
    
    events_collection.find_one_and_update(
        {'title': event_title},
        {'$inc': {'participants': 1}}
    )

    participations_collection.insert_one({'username': username, 'event_title': event_title})

    return redirect(url_for('participated_events'))

@app.route('/participated')
def participated_events():
    username = session.get('username')
    
    participations = participations_collection.find({'username': username})

    participated_events = []

    for participation in participations:
        event_title = participation.get('event_title')
        event = events_collection.find_one({'title': event_title})
        if event:
            participated_events.append(event)

    enumerated_events = list(enumerate(participated_events))

    return render_template('participated.html', events=enumerated_events)

@app.route('/myevents')
def my_events():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    hosted_events = events_collection.find({'host': username})
    return render_template('myevents.html', hosted_events=hosted_events)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)
