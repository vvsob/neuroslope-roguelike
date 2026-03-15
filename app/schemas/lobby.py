from pydantic import BaseModel


class LobbyCreate(BaseModel):
    character_id: int  # ID of the character the player wants to use in the game
