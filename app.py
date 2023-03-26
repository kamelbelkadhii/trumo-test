from flask import Flask, request, jsonify, redirect, url_for
from flask_pymongo import PyMongo
from flask_oauthlib.client import OAuth
from flask_jwt_extended import JWTManager, jwt_required, create_access_token

app = Flask(__name__)

app.config['MONGO_URI'] = 'mongodb://localhost:27017/kyc_db'
app.config['SECRET_KEY'] = '9498091b419f3d4adaaa8cf62a0d122f05d632997abc4e5dd892dbebdf73543a'
app.config['JWT_SECRET_KEY'] = '4e1bcf8957aa3fd8ad3525fb141d84ae1cbbb019074ea4484607e827f2f47ef9'

mongo = PyMongo(app)
oauth = OAuth(app)
jwt = JWTManager(app)

google = oauth.remote_app(
    'google',
    consumer_key='194568600552-a227bngq4k5m9d2mmbp2jrr6q8dijj2g.apps.googleusercontent.com',
    consumer_secret='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',
    request_token_params={
        'scope': 'email',
        'response_type': 'code'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login')
def login():
    return google.authorize(callback=url_for('authorized', _external=True))


@app.route('/login/authorized')
@google.authorized_handler
def authorized(resp):
    if resp is None:
        return 'Access denied.'

    access_token = resp['access_token']
    google_user_data = google.get('userinfo', token=(access_token, ''))

    email = google_user_data.data['email']
    user = mongo.db.users.find_one({'email': email})

    if not user:
        user = {'email': email}
        mongo.db.users.insert_one(user)
        user = mongo.db.users.find_one({'email': email})

    jwt_token = create_access_token(identity=str(user['_id']))
    return jsonify(access_token=jwt_token)



@app.route('/kyc', methods=['POST'])
@jwt_required()
def add_kyc():
    current_user = get_jwt_identity()
    kyc_data = request.get_json()

    kyc_record = {
        'user_id': ObjectId(current_user),
        'kyc_data': kyc_data
    }

    mongo.db.kyc.insert_one(kyc_record)
    return jsonify(message='KYC data added successfully.')


@app.route('/kyc', methods=['GET'])
@jwt_required()
def view_kyc():
    current_user = get_jwt_identity()
    kyc_data = mongo.db.kyc.find_one({'user_id': ObjectId(current_user)})
    return dumps(kyc_data)


if __name__ == '__main__':
    app.run(debug=True)

