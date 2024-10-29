from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import json
from bson import ObjectId
import requests
import datetime
import uuid
from flask_cors import CORS

app = Flask(__name__)
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)
    
uri = "mongodb+srv://xxgoldenprozxx:gsP8G7odnez1IBs2@chamber-of-reflection.0jcoz.mongodb.net/?retryWrites=true&w=majority&appName=chamber-of-reflection"
REVALIDATE_API_KEY="115a825b-27ba-479b-a023-4e7dcfa97767"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi("1"))
try:
    client.admin.command("ping")
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client["chamber-of-reflection"]

notes_collection = db["notes"]

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                "http://localhost:3000",
                "http://localhost:3001",
            ]
        }
    },
)   

@app.route("/")
def home():
    return "Server online", 200


@app.route("/add-note", methods=["POST"])
def add_note():
    data = request.json
    note_content = data.get("content")
    if not note_content and len(note_content) < 5:
        return (
            jsonify({"error": {"message": "Content is required."}}),
            400,
        )  # Bad Request
    try:
        date_posted = datetime.datetime.now(datetime.timezone.utc)
        note_id = str(uuid.uuid4())
        note_document = {
            "_id": note_id,  # Use proper keys for the document
            "date_posted": date_posted.isoformat(),  # Convert to ISO format for MongoDB
            "content": note_content,  # Key for the content
        }
        notes_collection.insert_one(note_document)
        url = "http://localhost:3000/api/revalidate"  # Adjust the URL as necessary
        data = {"tag": "reflections","revalidate_api_key":REVALIDATE_API_KEY}  # Specify the tag you want to revalidate

        response = requests.post(url, json=data)
        return (
            jsonify(
                {"message": "Note posted successfully!", "data": {"noteId": note_id}}
            ),
            201,
        )
    except Exception as e:
        print(e)
        return (
            jsonify(
                {
                    "error": {
                        "message": "Failed to post note",
                    }
                }
            ),
            500,
        )


@app.route("/get-notes", methods=["GET"])
def get_notes():
    try:
        # Define aggregation pipeline
        pipeline = [
            {
       
        "$addFields": {
            "time_posted": {
                "$dateToString": {
                    "format": "%H:%M",  # Format to "9:38 AM"
                    "date": {
                        "$dateFromString": {
                            "dateString": "$date_posted",
                            "onError": None,
                            "onNull": None
                        }
                    }
                }
            }
        }
    },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%B %d, %G",  # Desired date format
                            "date": {
                                "$dateFromString": {
                                    "dateString": "$date_posted",  # Original date string
                                    "onError": None,
                                    "onNull": None
                                }
                            }
                        }
                    },
                    "reflections": {"$push": "$$ROOT"}  # Collect all notes for that date
                }
            },
            {"$sort": {"_id": -1}}  # Sort by date in descending order
        ]

        # Run the aggregation
        reflections = list(notes_collection.aggregate(pipeline))
        print(reflections)
        if not reflections:
            return jsonify({"error": {"message": "Failed to fetch notes"}}), 404

        # Return the response
        return jsonify({
            "message": "Notes fetched successfully!",
            "data": {"reflections": reflections},
        }), 200

    except Exception as e:
        print(e)
        return jsonify({"error": {"message": "An unexpected error occurred"}}), 500



if __name__ == "__main__":
    app.run(debug=True)
