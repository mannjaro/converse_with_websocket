import json
import boto3
from botocore.exceptions import ClientError
from aws_lambda_powertools.utilities.typing.lambda_context import LambdaContext
from aws_lambda_powertools.logging import Logger

from websocket.weather_forecast import WeatherForecast

MODEL_ID = {
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
}

logger = Logger()


def handler(event: dict, context: LambdaContext):
    request_context = event["requestContext"]
    connection_id = request_context["connectionId"]
    domain_name = request_context["domainName"]
    stage = request_context["stage"]
    route_key = request_context["routeKey"]
    endpoint = f"https://{domain_name}/{stage}"
    body = event.get("body", "")
    logger.info(body)

    if route_key == "$connect":
        pass
    elif route_key == "$disconnect":
        pass
    else:
        if body:
            chat_with_bedrock(body, connection_id, endpoint)

    return {"statusCode": 200, "body": "Request processed."}


def send_message_to_all_connected(message, connection_id, endpoint):
    api_gateway_management_api = boto3.client(
        "apigatewaymanagementapi", endpoint_url=endpoint
    )
    payload = json.dumps(message)
    try:
        api_gateway_management_api.post_to_connection(
            ConnectionId=connection_id, Data=payload
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "GoneException":
            print(f"Connection {connection_id} is gone, skipping.")
        else:
            raise e


def chat_with_bedrock(message, connection_id: str, endpoint: str):
    schema = WeatherForecast.model_json_schema()
    # toolConfig = ToolsSchema(
    #     tools=[
    #         ToolSpec(
    #             name="get_weather",
    #             description="Get the current weather in given location",
    #             inputSchema={
    #                 "json": {"type": "object", "properties": schema["properties"]}
    #             },
    #         )
    #     ]
    # )
    toolConfig = {
        "tools": [
            {
                "toolSpec": {
                    "name": "get_weather",
                    "description": "Get the current weather in given location",
                    "inputSchema": {
                        "json": {"type": "object", "properties": schema["properties"]}
                    },
                }
            }
        ]
    }
    messages = [
        {"role": "user", "content": [{"text": "what is the weather in Tokyo?"}]}
    ]
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    stream, metadata = client.converse_stream(
        modelId=MODEL_ID["claude-3-sonnet"], messages=messages, toolConfig=toolConfig
    )
    for chunk in stream:
        send_message_to_all_connected(chunk, connection_id, endpoint)
