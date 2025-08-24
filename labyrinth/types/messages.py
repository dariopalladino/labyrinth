"""
Message types for Labyrinth.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from a2a import types as a2a_types


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"


class MessageType(str, Enum):
    """Message type enumeration."""
    TEXT = "text"
    FILE = "file"
    STRUCTURED = "structured"


class MessagePart(BaseModel):
    """Base class for message parts."""
    type: str
    
    class Config:
        extra = "allow"


class TextPart(MessagePart):
    """Text message part."""
    type: Literal["text"] = "text"
    content: str = Field(..., description="Text content")


class FilePart(MessagePart):
    """File message part."""
    type: Literal["file"] = "file"
    file_uri: Optional[str] = Field(None, description="File URI")
    file_bytes: Optional[bytes] = Field(None, description="File bytes")
    filename: str = Field(..., description="File name")
    mime_type: Optional[str] = Field(None, description="MIME type")


class StructuredPart(MessagePart):
    """Structured data message part."""
    type: Literal["structured"] = "structured"
    data: Dict[str, Any] = Field(..., description="Structured data")
    schema: Optional[Dict[str, Any]] = Field(None, description="Data schema")


class Message(BaseModel):
    """
    High-level message representation.
    """
    
    content: Union[str, List[MessagePart]] = Field(
        ..., 
        description="Message content - can be simple string or list of parts"
    )
    role: MessageRole = Field(
        default=MessageRole.USER, 
        description="Message role"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    timestamp: Optional[datetime] = Field(
        None,
        description="Message timestamp"
    )
    message_id: Optional[str] = Field(
        None,
        description="Unique message identifier"
    )
    
    def to_a2a_message(self) -> a2a_types.Message:
        """
        Convert to A2A SDK Message format.
        
        Returns:
            A2A SDK Message instance
        """
        # Convert content to A2A parts format
        parts = []
        
        if isinstance(self.content, str):
            # Simple string message
            parts.append(a2a_types.TextPart(content=self.content))
        else:
            # Complex message with multiple parts
            for part in self.content:
                if isinstance(part, TextPart):
                    parts.append(a2a_types.TextPart(content=part.content))
                elif isinstance(part, FilePart):
                    if part.file_uri:
                        parts.append(a2a_types.FileWithUri(
                            uri=part.file_uri,
                            name=part.filename,
                            mime_type=part.mime_type
                        ))
                    elif part.file_bytes:
                        parts.append(a2a_types.FileWithBytes(
                            bytes=part.file_bytes,
                            name=part.filename,
                            mime_type=part.mime_type
                        ))
                elif isinstance(part, StructuredPart):
                    parts.append(a2a_types.DataPart(data=part.data))
        
        return a2a_types.Message(
            role=a2a_types.Role(self.role.value),
            parts=parts
        )
    
    @classmethod
    def from_a2a_message(cls, a2a_message: a2a_types.Message) -> "Message":
        """
        Create Message from A2A SDK Message.
        
        Args:
            a2a_message: A2A SDK Message instance
            
        Returns:
            Message instance
        """
        parts = []
        
        for part in a2a_message.parts:
            if isinstance(part, a2a_types.TextPart):
                parts.append(TextPart(content=part.content))
            elif isinstance(part, (a2a_types.FileWithUri, a2a_types.FileWithBytes)):
                if hasattr(part, 'uri'):
                    parts.append(FilePart(
                        file_uri=part.uri,
                        filename=part.name,
                        mime_type=part.mime_type
                    ))
                else:
                    parts.append(FilePart(
                        file_bytes=part.bytes,
                        filename=part.name,
                        mime_type=part.mime_type
                    ))
            elif isinstance(part, a2a_types.DataPart):
                parts.append(StructuredPart(data=part.data))
        
        # If only one text part, use simple string content
        if len(parts) == 1 and isinstance(parts[0], TextPart):
            content = parts[0].content
        else:
            content = parts
            
        return cls(
            content=content,
            role=MessageRole(a2a_message.role.value),
        )
    
    @classmethod
    def text(cls, content: str, role: MessageRole = MessageRole.USER) -> "Message":
        """
        Create a simple text message.
        
        Args:
            content: Text content
            role: Message role
            
        Returns:
            Message instance
        """
        return cls(content=content, role=role)
    
    @classmethod 
    def file(cls, 
             filename: str, 
             file_uri: Optional[str] = None,
             file_bytes: Optional[bytes] = None,
             mime_type: Optional[str] = None,
             role: MessageRole = MessageRole.USER) -> "Message":
        """
        Create a file message.
        
        Args:
            filename: File name
            file_uri: File URI (if using URI reference)
            file_bytes: File bytes (if using direct bytes)
            mime_type: MIME type
            role: Message role
            
        Returns:
            Message instance
        """
        file_part = FilePart(
            filename=filename,
            file_uri=file_uri,
            file_bytes=file_bytes,
            mime_type=mime_type
        )
        return cls(content=[file_part], role=role)


class MessageResponse(BaseModel):
    """
    Response from sending a message.
    """
    
    message_id: str = Field(..., description="Unique message identifier")
    status: str = Field(..., description="Response status")
    content: Optional[str] = Field(None, description="Response content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    
    @property
    def is_success(self) -> bool:
        """Check if the response indicates success."""
        return self.status == "success" and not self.error
    
    @property
    def is_error(self) -> bool:
        """Check if the response indicates an error."""
        return self.status == "error" or bool(self.error)
    
    @classmethod
    def from_a2a_response(cls, response: a2a_types.SendMessageResponse) -> "MessageResponse":
        """
        Create MessageResponse from A2A SDK response.
        
        Args:
            response: A2A SDK response
            
        Returns:
            MessageResponse instance
        """
        if isinstance(response, a2a_types.SendMessageSuccessResponse):
            return cls(
                message_id=response.message_id,
                status="success"
            )
        else:
            # Handle error response
            error_msg = getattr(response, 'error', 'Unknown error')
            return cls(
                message_id="",
                status="error", 
                error=str(error_msg)
            )
