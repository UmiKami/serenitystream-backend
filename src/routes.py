import os
import json
from flask import Blueprint, request, jsonify
import boto3
import botocore
from datetime import datetime
import time

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

@api.route("/video", methods=["POST"])
def upload_file():
    video = request.files.get("video")

    if video is not None:
        s3.upload_fileobj(video, BUCKET_NAME, video.filename)
        return jsonify("Video upload DONE and is now being processed!"), 201
    
    return jsonify("There was an error uploading the video!"), 400

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