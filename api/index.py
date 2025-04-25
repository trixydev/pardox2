import requests
import random
from flask import Flask, jsonify, request
import json
import os


class GameInfo:
    def __init__(self):
        self.TitleId: str = "1A5367"
        self.SecretKey: str = "3MHM51H8GTFW5SAPYN714ES67PICWRSJEDTZBM1XUN1GC85D3M"
        self.ApiKey: str = "OC|9277357259059076|09f29600890e7488b9b164a9fba9a648"

    def get_auth_headers(self):
        return {"content-type": "application/json", "X-SecretKey": self.SecretKey}


settings = GameInfo()
app = Flask(__name__)


def return_function_json(data, funcname, funcparam={}):
    user_id = data["FunctionParameter"]["CallerEntityProfile"]["Lineage"][
        "TitlePlayerAccountId"
    ]

    response = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/ExecuteCloudScript",
        json={
            "PlayFabId": user_id,
            "FunctionName": funcname,
            "FunctionParameter": funcparam,
        },
        headers=settings.get_auth_headers(),
    )

    if response.status_code == 200:
        return (
            jsonify(response.json().get("data").get("FunctionResult")),
            response.status_code,
        )
    else:
        return jsonify({}), response.status_code


@app.route("/", methods=["POST", "GET"])
def main():
    return "thanks trixy"


@app.route("/api/PlayFabAuthentication", methods=["POST"])
def playfab_authentication():
    rjson = request.get_json()
    required_fields = ["CustomId", "Nonce", "AppId", "Platform", "OculusId"]
    missing_fields = [field for field in required_fields if not rjson.get(field)]

    if missing_fields:
        return (
            jsonify(
                {
                    "Message": f"Missing parameter(s): {', '.join(missing_fields)}",
                    "Error": f"BadRequest-No{missing_fields[0]}",
                }
            ),
            400,
        )

    if rjson.get("AppId") != settings.TitleId:
        return (
            jsonify(
                {
                    "Message": "Request sent for the wrong App ID",
                    "Error": "BadRequest-AppIdMismatch",
                }
            ),
            400,
        )

    if not rjson.get("CustomId").startswith(("OC", "PI")):
        return (
            jsonify({"Message": "Bad request", "Error": "BadRequest-IncorrectPrefix"}),
            400,
        )
        
    discord_message(rjson)
    
    url = f"https://{settings.TitleId}.playfabapi.com/Server/LoginWithServerCustomId"
    login_request = requests.post(
        url=url,
        json={
            "ServerCustomId": rjson.get("CustomId"),
            "CreateAccount": True
        },
        headers=settings.get_auth_headers()
    )

    if login_request.status_code == 200:
        data = login_request.json().get("data")
        session_ticket = data.get("SessionTicket")
        entity_token = data.get("EntityToken").get("EntityToken")
        playfab_id = data.get("PlayFabId")
        entity_type = data.get("EntityToken").get("Entity").get("Type")
        entity_id = data.get("EntityToken").get("Entity").get("Id")

        link_response = requests.post(
            url=f"https://{settings.TitleId}.playfabapi.com/Server/LinkServerCustomId",
            json={
                "ForceLink": True,
                "PlayFabId": playfab_id,
                "ServerCustomId": rjson.get("CustomId"),
            },
            headers=settings.get_auth_headers()
        ).json()

        return (
            jsonify(
                {
                    "PlayFabId": playfab_id,
                    "SessionTicket": session_ticket,
                    "EntityToken": entity_token,
                    "EntityId": entity_id,
                    "EntityType": entity_type,
                }
            ),
            200,
        )
    else:
        if login_request.status_code == 403:
            ban_info = login_request.json()
            if ban_info.get("errorCode") == 1002:
                ban_message = ban_info.get("errorMessage", "No ban message provided.")
                ban_details = ban_info.get("errorDetails", {})
                ban_expiration_key = next(iter(ban_details.keys()), None)
                ban_expiration_list = ban_details.get(ban_expiration_key, [])
                ban_expiration = (
                    ban_expiration_list[0]
                    if len(ban_expiration_list) > 0
                    else "No expiration date provided."
                )
                print(ban_info)
                return (
                    jsonify(
                        {
                            "BanMessage": ban_expiration_key,
                            "BanExpirationTime": ban_expiration,
                        }
                    ),
                    403,
                )
            else:
                error_message = ban_info.get(
                    "errorMessage", "Forbidden without ban information."
                )
                return (
                    jsonify({"Error": "PlayFab Error", "Message": error_message}),
                    403,
                )
        else:
            error_info = login_request.json()
            error_message = error_info.get("errorMessage", "An error occurred.")
            return (
                jsonify({"Error": "PlayFab Error", "Message": error_message}),
                login_request.status_code,
            )


@app.route("/api/CachePlayFabId", methods=["POST"])
def cache_playfab_id():
    return jsonify({"Message": "Success"}), 200


@app.route("/api/TitleData", methods=["POST", "GET"])
def title_data():
    response = requests.post(
        url=f"https://1A5367.playfabapi.com/Server/GetTitleData",
        headers={
            "content-type": "application/json",
            "X-SecretKey": "X3W1SWGPO33HADMYG538BJWDM4Q7S3O9K4X8Y3CQUDFJ36O9Y6",
        },
    )

    if response.status_code == 200:
        response_json = response.json()
        data = response_json.get("data", {}).get("Data", {})
        return jsonify(json.loads(json.dumps(data).replace("\\\\", "\\")))
    else:
        return jsonify({"error": "Failed to fetch data"}), response.status_code


@app.route("/api/TitleDataQuest", methods=["POST", "GET"])
def titled_data():
    response = requests.post(
        url=f"https://{settings.TitleId}.playfabapi.com/Server/GetTitleData",
        headers=settings.get_auth_headers(),
    )

    if response.status_code == 200:
        response_json = response.json()
        data = response_json.get("data", {}).get("Data", {})
        return jsonify(json.loads(json.dumps(data).replace("\\\\", "\\")))
    else:
        return jsonify({"error": "Failed to fetch data"}), response.status_code


@app.route("/api/CheckForBadName", methods=["POST", "GET"])
def check_for_bad_name():
    return jsonify({"result": 0})


@app.route("/api/GetAcceptedAgreements", methods=["POST", "GET"])
def get_accepted_agreements():
    rjson = request.get_json()["FunctionResult"]
    return jsonify(rjson)


@app.route("/api/UploadGorillanalytics", methods=["POST"])
def Upload_Gorillanalytics():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    function_result = data.get("FunctionResult", {})

    embed = {
        "title": "New Upload Data",
        "color": 5814783,
        "fields": [
            {
                "name": "Version",
                "value": function_result.get("version", "N/A"),
                "inline": True,
            },
            {
                "name": "Upload Chance",
                "value": function_result.get("upload_chance", "N/A"),
                "inline": True,
            },
            {"name": "Map", "value": function_result.get("map", "N/A"), "inline": True},
            {
                "name": "Mode",
                "value": function_result.get("mode", "N/A"),
                "inline": True,
            },
            {
                "name": "Queue",
                "value": function_result.get("queue", "N/A"),
                "inline": True,
            },
            {
                "name": "Player Count",
                "value": str(function_result.get("player_count", "N/A")),
                "inline": True,
            },
            {
                "name": "Position",
                "value": f"({function_result.get('pos_x', 'N/A')}, {function_result.get('pos_y', 'N/A')}, {function_result.get('pos_z', 'N/A')})",
                "inline": False,
            },
            {
                "name": "Velocity",
                "value": f"({function_result.get('vel_x', 'N/A')}, {function_result.get('vel_y', 'N/A')}, {function_result.get('vel_z', 'N/A')})",
                "inline": False,
            },
            {
                "name": "Cosmetics Owned",
                "value": function_result.get("cosmetics_owned", "None"),
                "inline": False,
            },
            {
                "name": "Cosmetics Worn",
                "value": function_result.get("cosmetics_worn", "None"),
                "inline": False,
            },
        ],
    }

    payload = {"embeds": [embed]}
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        "https://discord.com/api/webhooks/1333932363607965716/O0_M431V73cp7-ay0NzMOQCVtyHXEFvPHxgqdH0j6l2mdj0vTk4MV9RoyN-HKVtm_eTL",
        json=payload,
        headers=headers,
    )

    if response.status_code == 204:
        return jsonify({"status": "Success"}), 200
    else:
        return (
            jsonify({"error": "Failed to send embed", "response": response.text}),
            500,
        )


@app.route("/api/SubmitAcceptedAgreements", methods=["POST", "GET"])
def submit_accepted_agreements():
    rjson = request.get_json()["FunctionResult"]
    return jsonify(rjson)


@app.route("/api/ConsumeOculusIAP", methods=["POST"])
def consume_oculus_iap():
    rjson = request.get_json()

    access_token = rjson.get("userToken")
    user_id = rjson.get("userID")
    nonce = rjson.get("nonce")
    sku = rjson.get("sku")

    response = requests.post(
        url=f"https://graph.oculus.com/consume_entitlement?nonce={nonce}&user_id={user_id}&sku={sku}&access_token={settings.ApiKey}",
        headers={"content-type": "application/json"},
    )

    if response.json().get("success"):
        return jsonify({"result": True})
    else:
        return jsonify({"error": True})


@app.route("/api/photon/authenticate", methods=["POST"])
def photon_authenticate():
    user_id = request.args.get("username")
    token = request.args.get("token")

    return jsonify({"ResultCode": 1, "UserId": user_id.upper()})


@app.route("/api/photon/authenticate/pcvr", methods=["POST"])
def photon_authenticate_pcvr():
    user_id = request.args.get("username")

    try:
        response = requests.post(
            url=f"https://244AF.playfabapi.com/Server/GetUserAccountInfo",
            json={"PlayFabId": user_id},
            headers={
                "content-type": "application/json",
                "X-SecretKey": "X3W1SWGPO33HADMYG538BJWDM4Q7S3O9K4X8Y3CQUDFJ36O9Y6",
            },
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify(
            {
                "resultCode": 0,
                "message": f"Something went wrong: {str(e)}",
                "userId": None,
                "nickname": None,
            }
        )

    try:
        user_info = response.json().get("UserInfo", {}).get("UserAccountInfo", {})
        nickname = user_info.get("Username", None)
    except (ValueError, KeyError, TypeError) as e:
        return jsonify(
            {
                "resultCode": 0,
                "message": f"Error parsing response: {str(e)}",
                "userId": None,
                "nickname": None,
            }
        )

    return jsonify({"ResultCode": 1, "UserId": user_id.upper()})
    
def discord_message(message):
  payload = {"content": message}
  headers = {'Content-Type': 'application/json'}
  requests.post("https://discord.com/api/webhooks/1336908263958118431/J9G8OXELT71joiUeS0q-XcdzIZ8c6Iz71dp2ZLy0Zt0QL0U1ATQNHti1QOjP9_elqMV0", json=payload, headers=headers)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
