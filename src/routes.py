import os
import json
from flask import Blueprint, request, jsonify
import boto3
import botocore
from datetime import datetime
import time
import re
from ast import literal_eval


# Set up blueprint to which prefix will be applied
api = Blueprint("api", __name__)

# AWS S3 Bucket Connection Set Up
s3 = boto3.client("s3", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get(
    "AWS_SECRET_ACCESS_KEY"), region_name="us-east-1")  # access keys are private so they should never be available to the public
db = boto3.client("dynamodb", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                  aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"), region_name="us-east-1")
auth = boto3.client("cognito-idp", aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"), region_name="us-east-1")
ecoder = boto3.client("elastictranscoder", aws_access_key_id=os.environ.get(
    "AWS_ACCESS_KEY_ID"), aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"), region_name="us-east-1")

# s3 methods require you to provide the bucket name every time so we store it for efficiency
BUCKET_NAME = "visual-media-bucket"
COMPRESS_BUCKET_NAME = "processed-media-gamingforum"
AWS_REGION = "us-east-1"  # some methods require region to be specify

@api.route('/')
def home():
    return 'Peace sweet peace! <strong> Your Yoga API! <strong>'

######################################################
### VIDEO SECTION


@api.route("/videos/public", methods=["GET"])
def get_all_videos():
    response = db.scan(
        TableName="serenity_videos",
        Limit=20,
        Select="ALL_ATTRIBUTES"
    )


    # turns comment strings into proper dictionaries
    for item in response["Items"]:
        comments = item["comments"]["SS"]
        for index, comment in enumerate(comments):
            comments[index] = literal_eval(json.loads(json.dumps(comment)))


    return jsonify(response), 200

@api.route("/videos", methods=["POST"])
def upload_file():
    token = request.headers.get("Authorization").split(" ")[1]
    video = request.files.get("videoFile")
    video_title = request.form.get("videoTitle")
    video_title = re.sub(" +", " ", video_title )
    try:
        user = auth.get_user(AccessToken = token)
        username = user["Username"]
    except (botocore.exceptions.ClientError) as err:
        error_code = err.response["Error"]['Code']

        if error_code == "NotAuthorizedException":
            return jsonify("Invalid session!"), 400

    if video_title is None:
        return jsonify("No video title privided!"), 400

    if video is not None:
        video.filename = username + "^" + video_title + ".mp4"
        s3.upload_fileobj(video, BUCKET_NAME, video.filename)
        return jsonify("Video upload DONE and is now being processed!"), 201
    
    return jsonify("There was an error uploading the video!"), 400


@api.route("/videos/<string:id>", methods=['GET'])
def get_video_details(id):
    videoDetails = db.get_item(TableName="serenity_videos", Key={ 
        "id": {
            "S": id
        }
    })

    if "Item" in videoDetails:
        comments = videoDetails["Item"]["comments"]["SS"]

        # turns array of strings to array of json objects
        for index, comment in enumerate(comments):
            comments[index] = literal_eval(json.loads(json.dumps(comment)))

        return jsonify(videoDetails["Item"]), 200
    
    return jsonify("video does not exist"), 400

@api.route("/videos/<string:id>/comment", methods=["POST"])
def add_comment_to_video(id):
    body_request =  request.get_json(force=True)
    token = request.headers.get("Authorization").split(" ")[1]
    
    try:
        user = auth.get_user(AccessToken = token)
        username = user["Username"]
    except (botocore.exceptions.ClientError) as err:
        error_code = err.response["Error"]['Code']

        if error_code == "NotAuthorizedException":
            return jsonify("Invalid session!"), 400
        
    comment = {
        "username": username,
        "content": body_request["comment"]
    }

    try:
        # Get the existing item from DynamoDB
        response = db.get_item(
            TableName='serenity_videos',
            Key={'id': {'S': id}}
        )

        item = response['Item']
        
        # Update the 'comments' attribute with the new comment
        existing_comments = item['comments']['SS']
        existing_comments.append(str(comment))
        db.update_item(
            TableName='serenity_videos',
            Key={'id': {'S': id}},
            UpdateExpression='SET comments = :val',
            ExpressionAttributeValues={
                ':val': {'SS': existing_comments}
            }
        )
        
        # Return a success message
        return jsonify({'message': 'Comment added successfully'})
        
    except botocore.exceptions.ClientError as e:
        # Return an error message if the item cannot be retrieved or updated
        print(e)

        return jsonify({'message': 'Error adding comment'}), 500

    


######################################################
### AUTH SECTION

@api.route("/auth/signup", methods=["POST"])
def create_user_account():
    request_body = request.get_json(force=True)

    age = "18"
    name = request_body["name"]
    username = request_body["username"]
    email = request_body["email"]
    password = request_body["password"]

    # Create a datetime object representing the current time
    now = datetime.now()

    # Convert the datetime object to a Unix timestamp
    unix_timestamp = int(time.mktime(now.timetuple()))


    try:
        aws_auth_res = auth.sign_up(
            ClientId=os.environ.get("AWS_COGNITO_CLIENT_ID"),
            Username=username,
            Password=password,
            UserAttributes=[
                {
                    "Name": "email",
                    "Value": email
                },
                {
                    "Name": "custom:age",
                    "Value": str(age)
                },
                {
                    "Name": "name",
                    "Value": name
                },
                {
                    "Name": "updated_at",
                    "Value": str(unix_timestamp)
                },

            ]
        )
    except (botocore.exceptions.ClientError) as err:
        error_code = err.response["Error"]['Code']

        if error_code == 'InvalidPasswordException':
            return jsonify("Invalid password!"), 400

        if error_code == 'UsernameExistsException':
            return jsonify("User already exits!"), 400
        
        if error_code == 'UserLambdaValidationException':
            return jsonify("Email already exists"), 400

        return jsonify("Something went wrong"), 400

    return jsonify(aws_auth_res)

@api.route("/auth/account/verification", methods=["POST"])
def confirm_registration():
    request_body = request.get_json(force=True)

    code = request_body["confirmation_code"]
    username = request_body["username"]

    try:
        aws_auth_res = auth.confirm_sign_up(
            ClientId=os.environ.get("AWS_COGNITO_CLIENT_ID"),
            Username=username,
            ConfirmationCode=code
        )
    except Exception as e:
        print(e)

        return jsonify("Something went wrong! Try again later."), 400


    return jsonify(aws_auth_res)

@api.route("/auth/login", methods=["POST"])
def signin_user_account():
    request_body = request.get_json(force=True)

    username = request_body["username"] if "username" in request_body else request_body["email"]
    password = request_body["password"]

    try:
        aws_auth_res = auth.initiate_auth(
            ClientId=os.environ.get("AWS_COGNITO_CLIENT_ID"),
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
    except (botocore.exceptions.ClientError) as err:
        error_code = err.response["Error"]['Code']

        if error_code == 'NotAuthorizedException':
            return jsonify(err.response["Error"]["Message"]), 400

        return jsonify("Something went wrong"), 400

    return jsonify(aws_auth_res)