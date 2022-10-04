import os
import random
import json
import socket

from datetime import datetime
from flask import Flask, request, make_response, render_template,redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
basedir = os.path.abspath(os.path.dirname(__file__))
dburi  = os.environ.get('DB_URL', 'sqlite:///' + os.path.join(basedir, 'data/app.db'))
print(dburi)
app.config['SQLALCHEMY_DATABASE_URI'] = dburi
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

db = SQLAlchemy(app)

class User(db.Model):
  id       = db.Column(db.Integer, primary_key=True,autoincrement = True)
  name     = db.Column(db.String(30), unique=True)
  mail     = db.Column(db.String(30), unique=True)
  password = db.Column(db.String(90))

class Poll(db.Model):
  id       = db.Column(db.Integer, primary_key=True)
  name     = db.Column(db.String(30), unique=True)
  question = db.Column(db.String(90))
  stamp    = db.Column(db.DateTime)
  options  = db.relationship('Option', backref='option', lazy='dynamic')

  def __init__(self, name, question, stamp=None):
      self.name  = name
      self.question = question
      if stamp is None:
         stamp = datetime.utcnow()
      self.stamp = stamp

class Option(db.Model):
  id      = db.Column(db.Integer, primary_key=True)
  text    = db.Column(db.String(30))
  poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'))
  poll    = db.relationship('Poll', backref=db.backref('poll', lazy='dynamic'))
  votes   = db.Column(db.Integer)

  def __init__(self, text, poll, votes):
      self.text = text
      self.poll = poll
      self.votes = votes


db.create_all()
db.session.commit()
hostname = socket.gethostname()
   
print("Check if a poll already exists into db")
# TODO check the latest one filtered by timestamp
poll = Poll.query.first()

if poll:
   print("Restart the poll")
   poll.stamp = datetime.utcnow()
   db.session.commit()

else:
   print("Load seed data from file")
   try: 
      with open(os.path.join(basedir, 'seeds/seed_data.json')) as file:
         seed_data = json.load(file)
         print("Start a new poll")
         poll = Poll(seed_data['poll'], seed_data['question'])
         db.session.add(poll)
         for i in seed_data['options']:
               option = Option(i, poll, 0)
               db.session.add(option)
         db.session.commit()
   except:
      print ("Cannot load seed data from file")
      poll = Poll("", "")



@app.route('/')
@app.route('/index.html')
def index():
   if not session.get("name"):return redirect("/login")
   hostname="hostname"
   poll = Poll.query.first()
   return render_template('index.html', hostname=hostname, poll=poll)


@app.route("/logout", methods=[ "GET"])
def logout():
   session["name"] = None
   return redirect("/")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
      print(request.form.get("email"))
      user=User(name=request.form.get("name"),mail=request.form.get("mail"),
      password=request.form.get("pass"))
      db.session.add(user)
      db.session.commit()
      session["name"] = user.name
      return redirect("/")
    return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
   if request.method == "POST":
      from sqlalchemy import or_,and_
      name=request.form.get("name")
      password=request.form.get("pass")
      user = User.query.filter(and_(or_(User.name == name, User.mail == name),User.password == password)).first()
      if not user:
         return "Unidentified!"
      session["name"] = name
      return redirect("/")
   return render_template("login.html")

@app.route("/simple.png")
def simple():
   import datetime
   from io import StringIO,BytesIO
   import random
   import matplotlib
   matplotlib.use('Agg')
   from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
   from matplotlib.figure import Figure
   from matplotlib.dates import DateFormatter
   fig=Figure()
   if 1==2:
      ax=fig.add_subplot(111)
      x=[]
      y=[]
      now=datetime.datetime.now()
      delta=datetime.timedelta(days=1)
      for i in range(10):
         x.append(now)
         now+=delta
         y.append(random.randint(0, 1000))
      ax.plot_date(x, y, '-')
      ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
      fig.autofmt_xdate()

   #ax = fig.add_axes([0,0,1,1])
   #langs = ['C', 'C++', 'Java', 'Python', 'PHP']
   #students = [23,17,35,29,12]
   #ax.barh(langs,students)
   #fig.ylabel('Product')
   #fig.xlabel('Quantity')
   results = Option.query.filter_by(poll_id=poll.id).all()
   Product = []

   Quantity = []
   for r in results:
      Product.append(r.text)
      Quantity.append(r.votes)


   import matplotlib.pyplot as plt

   plt.barh(Product,Quantity)
   plt.title('Votes')
   plt.ylabel('Teams')
   


   #canvas=FigureCanvas(plt.figure(0))

   png_output = BytesIO()
   #canvas.print_png(png_output)
   plt.savefig(png_output)
   plt.close() 
   response=make_response(png_output.getvalue())
   response.headers['Content-Type'] = 'image/png'
   return response

@app.route('/vote.html', methods=['POST','GET'])
def vote():
   if not session.get("name"):return redirect("/login")
   has_voted = False
   vote_stamp = request.cookies.get('vote_stamp')
   hostname="hostname"
   poll = Poll.query.first()
   if request.method == 'POST':
      has_voted = True
      vote = request.form['vote']
      if vote_stamp:
         print ("This client has already has voted! His vote stamp is : " + vote_stamp)
      else:
         print ("This client has not voted yet!")
      voted_option = Option.query.filter_by(poll_id=poll.id,id=vote).first() 
      voted_option.votes += 1
      db.session.commit()
   
   # if request.method == 'GET':
   options = Option.query.filter_by(poll_id=poll.id).all()        
   resp = make_response(render_template('vote.html', hostname=hostname, poll=poll, options=options))
   
   if has_voted:
      vote_stamp = hex(random.getrandbits(64))[2:-1]
      print ("Set coookie for voted")
      resp.set_cookie('vote_stamp', vote_stamp)
   
   return resp

@app.route('/results.html')
def results():
   if not session.get("name"):return redirect("/login")
   results = Option.query.filter_by(poll_id=poll.id).all()
   poll = Poll.query.first()
   return render_template('results.html', hostname=hostname, poll=poll, results=results)

@app.route("/matplot-as-image-<int:num_x_points>.png")
def plot_png(num_x_points=50):
    """ renders the plot on the fly.
    """
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    x_points = range(num_x_points)
    axis.plot(x_points, [random.randint(1, 30) for x in x_points])

    output = io.BytesIO()
    FigureCanvasAgg(fig).print_png(output)
    return Response(output.getvalue(), mimetype="image/png")


@app.route("/matplot-as-image-<int:num_x_points>.svg")
def plot_svg(num_x_points=50):
    """ renders the plot on the fly.
    """
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    x_points = range(num_x_points)
    axis.plot(x_points, [random.randint(1, 30) for x in x_points])

    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype="image/svg+xml")



    
    #app.run(host='0.0.0.0', port=5000, debug=False)

