from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from .response import ToolCall

@dataclass
class TurnState:
    '''
    Represents the state of a single logical turn in a conversation.
    A turn typically encompasses an input, any resulting tool calls,
    and the final response for that segment of interaction.
    '''
    turn_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    # Stores messages specific to this turn, including user input, assistant thoughts,
    # tool call requests, tool results, and final assistant response for the turn.

    tool_calls: List[ToolCall] = field(default_factory=list)
    # Records actual ToolCall objects (name, args, result) made during this turn.

    metadata: Dict[str, Any] = field(default_factory=dict)
    # Flexible dictionary for additional turn-specific data, e.g.,
    # rewards, success flags, alternative responses, environment state relevant to this turn.

@dataclass
class ConversationState:
    '''
    Represents the complete state of a conversation, composed of multiple turns.
    This structure is intended for more detailed tracking and analysis,
    especially for training or debugging purposes.
    '''
    conversation_id: str
    turns: List[TurnState] = field(default_factory=list)
    # An ordered list of TurnState objects, representing the progression of the conversation.

    metadata: Dict[str, Any] = field(default_factory=dict)
    # Flexible dictionary for data applicable to the entire conversation, 
    # e.g., overall task goals, user profile, session settings.

    def get_last_turn(self) -> Optional[TurnState]:
        '''Returns the last turn in the conversation, if any.'''
        return self.turns[-1] if self.turns else None

    def add_turn(self, turn: TurnState) -> None:
        '''Adds a new turn to the conversation's history.'''
        self.turns.append(turn) 