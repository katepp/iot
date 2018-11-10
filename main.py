import json
import datetime
import requests
import gridfs
import uuid
import io

from pymongo import MongoClient,DESCENDING
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS, cross_origin
from src import *

def get_db():
    db = MongoClient('mongodb://root:example@mongo').iotDB
    return db

def process(image):
    v = '1'
    c = 'th'
    sk = "sk_d37c8e48696ae65c5b1ee8d7"
    url = "https://api.openalpr.com/v2/recognize?recognize_vehicle=%s&country=%s&secret_key=%s"%(v,c,sk)
    r = requests.post(url, files={'image': image})
    response = r.json()
    results = response['results']
    candidates = results[0]['candidates']
    return candidates[0]

app = Flask(__name__)
CORS(app)
@app.route("/")
def Hello():
    return "Hello IoT hahah fuck you"

@app.route("/getimage/<filename>", methods= ['GET'])
def getImage(filename):
    db = get_db()
    fs = gridfs.GridFS(db)    
    image = fs.find_one({'filename': filename})
    return send_file(io.BytesIO(image.read()),mimetype = 'image/png')

@app.route("/jenny/<action>", methods= ['GET'])
def jenny(action):
    if  request.method == 'GET':
        db = get_db()
        fs = gridfs.GridFS(db)
        results = db.log.find(
            {
                'action': action
            }
        ).sort([("time",DESCENDING)]).limit(1)

        data = {}
        for result in results:
            data = {
                'plate':    result['plate'],
                'time':     result['time'],
                'image':    result['image']
            }

        memmbers = db.licensePlate.count({'plate':data['plate']})
        if memmbers == 0:
            data['position'] = 'visitor'
        else:
            data['position'] = 'staff'
    return jsonify(data)

@app.route("/register", methods = ['POST'])
def register():
    if request.method == 'POST':
        plate = request.form['plate']
        name = request.form['name']
        db = get_db()
        db.licensePlate.insert_one(
            {
                "plate": plate,
                "name": name,
                "postion": 'staff'
            }
        )
    return "Data inserted successfully"

@app.route("/openalpr", methods = ['POST'])
def openalpr():
    if request.method == 'POST':

        image = request.files['image'].read()
        result = process(image)

        plate = result['plate']
        action = request.form['action']
        time = datetime.datetime.utcnow()

        db = get_db()
        fs = gridfs.GridFS(db)
        image_data = image
        image_filename = '.'.join([str(uuid.uuid4()), 'jpg'])
        image_id = fs.put(image_data, filename=image_filename) 
        db.log.insert_one(
            {
                'plate':    plate,
                'time':     time,
                'action':   action,
                'image':    '/'.join(['api', 'getimage', image_filename])
            }
        )

    return "Fuck yeah" 

@app.route("/statistic/<req>", methods = ['GET'])
def statistic(req):
    today = datetime.datetime.utcnow()
    start = datetime.datetime(today.year, today.month, today.day, 0, 0)
    end = datetime.datetime(today.year, today.month, today.day, 23, 59)
    db = get_db()
    data = []

    if  request.method == 'GET':
        if req == 'entrance' or req == 'exit':
            results = db.log.find({'time':{'$lte':end, '$gte':start}, 'action':req})
            for result in results:
                data.append(result['time'].hour)

            output = []
            for i in range(0,25):
                output.append(0)

            for i in range(0,25):
                output[i] = data.count(i)

        elif req == 'user':
            results = db.log.find({'time':{'$lte':end, '$gte':start}})
            output = {'staff':0, 'visitor':0}
            for result in results:
                memmbers = db.licensePlate.count({'plate':result['plate']})
                if memmbers == 0:
                    output['visitor'] = output['visitor']+1
                else:
                    output['staff'] = output['staff']+1
        # elif req == 'rank':
        #     results = db.log.group({
        #         { 'plate': 1 },
        #         { ord_dt: { $gt: new Date( '01/01/2012' ) } },
        #         function ( curr, result ) { },
        #         initial: { }

        #     })
        #     output = []

        return jsonify(output)
 