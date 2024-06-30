from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class ToolResult(BaseModel):
    toolUseId: str = Field(..., description="tool use id")
    content: List[dict] = Field(..., description="tool result content")
    status: Optional[Literal["success", "error"]] = Field(default="success")
