import * as path from "node:path";
import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import * as integrations from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { PolicyStatement, Effect } from "aws-cdk-lib/aws-iam";

export class WebsocketSampleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bedrockAccessPolicy = new PolicyStatement({
      effect: Effect.ALLOW,
      // See: https://docs.aws.amazon.com/ja_jp/service-authorization/latest/reference/list_amazonbedrock.html
      actions: ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      resources: ["*"],
    });

    const handler = new PythonFunction(this, "WebSocketHandler", {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      entry: path.join(__dirname, "../lambda/websocket"),
      handler: "handler",
      timeout: cdk.Duration.minutes(15),
    });
    handler.addToRolePolicy(bedrockAccessPolicy);

    const webSocketApi = new apigwv2.WebSocketApi(this, "WebsocketApi", {
      connectRouteOptions: {
        integration: new integrations.WebSocketLambdaIntegration(
          "ConnectIntegration",
          handler,
        ),
      },
      disconnectRouteOptions: {
        integration: new integrations.WebSocketLambdaIntegration(
          "DisconnectIntegration",
          handler,
        ),
      },
      defaultRouteOptions: {
        integration: new integrations.WebSocketLambdaIntegration(
          "DefaultIntegration",
          handler,
        ),
      },
    });
    new apigwv2.WebSocketStage(this, "WebSocketStage", {
      webSocketApi,
      stageName: "dev",
      autoDeploy: true,
    });
    handler.addEnvironment("WEBSOCKET_ENDPOINT", webSocketApi.apiEndpoint);
    handler.addToRolePolicy(
      new PolicyStatement({
        actions: ["execute-api:ManageConnections"],
        resources: [webSocketApi.arnForExecuteApi("POST", "/@connections/*")],
      }),
    );
  }
}
