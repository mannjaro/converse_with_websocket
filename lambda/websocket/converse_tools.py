import boto3
from weather_forecast import WeatherForecast, get_weather
from schema import ToolResult

MODEL_ID = {
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
}


class BedrockChat:
    def __init__(self, region="us-east-1"):
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.tool_dict = {"get_weather": get_weather}

    def parse_stream(self, response_stream):
        """
        Extract the LLM's output and tool's input from the streaming response.
        """
        for event in response_stream:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    yield delta["text"]

    def create_tool_config(self):
        """
        Create tool configuration for Bedrock.
        """
        schema = WeatherForecast.model_json_schema()
        return {
            "tools": [
                {
                    "toolSpec": {
                        "name": "get_weather",
                        "description": "Get the current weather in given location",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": schema["properties"],
                            }
                        },
                    }
                }
            ]
        }

    def converse_with_bedrock(self, model_id, messages, tool_config):
        """
        Perform conversation with Bedrock.
        """
        response = self.client.converse(
            modelId=model_id, messages=messages, toolConfig=tool_config
        )
        return response

    def handle_tool_use(self, tool):
        """
        Handle the tool use logic.
        """
        tool_result = {}
        try:
            result = self.tool_dict[tool["name"]](tool["input"])
            tool_result = ToolResult(
                toolUseId=tool["toolUseId"],
                content=[{"json": {"result": result}}],
            )
        except Exception as e:
            tool_result = ToolResult(
                toolUseId=tool["toolUseId"],
                content=[{"text": str(e)}],
                status="error",
            )
        return tool_result

    def chat(self, message):
        """
        Chat with Bedrock model.
        """
        messages = [{"role": "user", "content": [{"text": message}]}]
        tool_config = self.create_tool_config()

        response = self.converse_with_bedrock(
            MODEL_ID["claude-3-haiku"], messages, tool_config
        )
        ai_message = response["output"]["message"]
        messages.append(ai_message)
        stop_reason = response["stopReason"]

        if stop_reason == "tool_use":
            for content in ai_message["content"]:
                if content.get("toolUse"):
                    tool = content.get("toolUse")
                    tool_result = self.handle_tool_use(tool)
                    tool_result_message = {
                        "role": "user",
                        "content": [{"toolResult": tool_result.model_dump()}],
                    }
                    messages.append(tool_result_message)

        response = self.client.converse_stream(
            modelId=MODEL_ID["claude-3-sonnet"],
            messages=messages,
            toolConfig=tool_config,
        )

        ai_message_text = ""
        for chunk in self.parse_stream(response["stream"]):
            ai_message_text += chunk
            print(chunk, flush=True, end="")

        messages.append({"role": "assistant", "content": [{"text": ai_message_text}]})


if __name__ == "__main__":
    bedrock_chat = BedrockChat()
    bedrock_chat.chat("What's the weather in Osaka?")
