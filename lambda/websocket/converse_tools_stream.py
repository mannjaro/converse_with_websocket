import json
import boto3
from websocket.weather_forecast import WeatherForecast, get_weather
from schema import ToolResult

MODEL_ID = {
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
}

tool_use_args = {
    "input": {},
    "name": "",
    "toolUseId": "",
}


def parse_stream(response_stream):
    #  extract the LLM's output and tool's input from the streaming response.
    tool_use_input = ""
    for event in response_stream:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"]["delta"]
            if "text" in delta:
                yield delta["text"]
            if "toolUse" in delta:
                tool_use_input += delta["toolUse"]["input"]

        if "contentBlockStart" in event:
            tool_use_args.update(event["contentBlockStart"]["start"]["toolUse"])

        if "messageStop" in event:
            stop_reason = event["messageStop"]["stopReason"]
            if stop_reason == "tool_use":
                tool_use_args["input"] = json.loads(tool_use_input)


def chat_with_bedrock(message):
    schema = WeatherForecast.model_json_schema()
    messages = [{"role": "user", "content": [{"text": message}]}]
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
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    response = client.converse_stream(
        modelId=MODEL_ID["claude-3-sonnet"], messages=messages, toolConfig=toolConfig
    )
    for chunk in parse_stream(response_stream=response["stream"]):
        print(chunk, flush=True, end="")
    if tool_use_args["input"] is not None:
        tool_message = {"role": "assistant", "content": [{"toolUse": tool_use_args}]}
        messages.append(tool_message)
        weather = get_weather(tool_use_args["input"])
        toolResult = ToolResult(
            toolUseId=tool_use_args["toolUseId"],
            content=[{"json": {"result": weather}}],
        )
        tool_result_message = {
            "role": "user",
            "content": [{"toolResult": toolResult.model_dump()}],
        }
        messages.append(tool_result_message)
        response = client.converse_stream(
            modelId=MODEL_ID["claude-3-sonnet"],
            messages=messages,
            toolConfig=toolConfig,
        )
        for chunk in parse_stream(response_stream=response["stream"]):
            print(chunk, flush=True, end="")


if __name__ == "__main__":
    # schema = WeatherForecast.model_json_schema()
    # print(json.dumps(schema, indent=2))
    chat_with_bedrock("What the weather in Osaka?")
