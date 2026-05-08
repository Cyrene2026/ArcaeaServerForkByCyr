from __future__ import annotations

from fastapi import Form
from pydantic import BaseModel, ConfigDict, Field


class GameFormModel(BaseModel):
    model_config = ConfigDict(extra='ignore')


class GameLoginForm(GameFormModel):
    grant_type: str = Field(..., description='OAuth-style grant type sent by the client.')

    @classmethod
    def as_form(cls, grant_type: str = Form(...)):
        return cls(grant_type=grant_type)


class GameRegisterForm(GameFormModel):
    name: str
    password: str
    email: str
    device_id: str = 'low_version'
    is_allow_marketing_email: str | None = None

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        password: str = Form(...),
        email: str = Form(...),
        device_id: str = Form('low_version'),
        is_allow_marketing_email: str | None = Form(None),
    ):
        return cls(
            name=name,
            password=password,
            email=email,
            device_id=device_id,
            is_allow_marketing_email=is_allow_marketing_email,
        )


class FriendAddForm(GameFormModel):
    friend_code: str

    @classmethod
    def as_form(cls, friend_code: str = Form(...)):
        return cls(friend_code=friend_code)


class FriendDeleteForm(GameFormModel):
    friend_id: int

    @classmethod
    def as_form(cls, friend_id: int = Form(...)):
        return cls(friend_id=friend_id)


class CharacterChangeForm(GameFormModel):
    character: int
    skill_sealed: str = 'false'

    @classmethod
    def as_form(
        cls,
        character: int = Form(...),
        skill_sealed: str = Form('false'),
    ):
        return cls(character=character, skill_sealed=skill_sealed)


class CharacterExpForm(GameFormModel):
    amount: int

    @classmethod
    def as_form(cls, amount: int = Form(...)):
        return cls(amount=amount)


class UserSettingForm(GameFormModel):
    value: str

    @classmethod
    def as_form(cls, value: str = Form(...)):
        return cls(value=value)


class PurchasePackForm(GameFormModel):
    pack_id: str | None = None
    single_id: str | None = None

    @classmethod
    def as_form(
        cls,
        pack_id: str | None = Form(None),
        single_id: str | None = Form(None),
    ):
        return cls(pack_id=pack_id, single_id=single_id)


class PurchaseItemForm(GameFormModel):
    item_id: str

    @classmethod
    def as_form(cls, item_id: str = Form(...)):
        return cls(item_id=item_id)


class RedeemCodeForm(GameFormModel):
    code: str

    @classmethod
    def as_form(cls, code: str = Form(...)):
        return cls(code=code)


class ScoreTokenWorldQuery(GameFormModel):
    song_id: str
    difficulty: int
    stamina_multiply: int = 1
    fragment_multiply: int = 100
    prog_boost_multiply: int = 0
    beyond_boost_gauge_use: int = 0
    skill_id: str | None = None
    is_skill_sealed: str | None = None


class ScoreTokenCourseQuery(GameFormModel):
    course_id: str
    previous_token: str | None = None
    use_course_skip_purchase: str = 'false'


class SongScoreQuery(GameFormModel):
    song_id: str
    difficulty: int


class SongScorePostForm(GameFormModel):
    song_token: str
    song_hash: str
    song_id: str
    difficulty: int
    score: int
    shiny_perfect_count: int
    perfect_count: int
    near_count: int
    miss_count: int
    health: int
    modifier: int
    clear_type: int
    beyond_gauge: int
    submission_hash: str
    combo_interval_bonus: int | None = None
    hp_interval_bonus: int | None = None
    fever_bonus: int | None = None
    rank_bonus: int | None = None
    maya_gauge: int | None = None
    nextstage_bonus: int | None = None
    highest_health: int | None = None
    lowest_health: int | None = None
    room_code: str | None = None
    room_total_score: int | None = None
    room_total_players: int | None = None

    @classmethod
    def as_form(
        cls,
        song_token: str = Form(...),
        song_hash: str = Form(...),
        song_id: str = Form(...),
        difficulty: int = Form(...),
        score: int = Form(...),
        shiny_perfect_count: int = Form(...),
        perfect_count: int = Form(...),
        near_count: int = Form(...),
        miss_count: int = Form(...),
        health: int = Form(...),
        modifier: int = Form(...),
        clear_type: int = Form(...),
        beyond_gauge: int = Form(...),
        submission_hash: str = Form(...),
        combo_interval_bonus: int | None = Form(None),
        hp_interval_bonus: int | None = Form(None),
        fever_bonus: int | None = Form(None),
        rank_bonus: int | None = Form(None),
        maya_gauge: int | None = Form(None),
        nextstage_bonus: int | None = Form(None),
        highest_health: int | None = Form(None),
        lowest_health: int | None = Form(None),
        room_code: str | None = Form(None),
        room_total_score: int | None = Form(None),
        room_total_players: int | None = Form(None),
    ):
        return cls(
            song_token=song_token,
            song_hash=song_hash,
            song_id=song_id,
            difficulty=difficulty,
            score=score,
            shiny_perfect_count=shiny_perfect_count,
            perfect_count=perfect_count,
            near_count=near_count,
            miss_count=miss_count,
            health=health,
            modifier=modifier,
            clear_type=clear_type,
            beyond_gauge=beyond_gauge,
            submission_hash=submission_hash,
            combo_interval_bonus=combo_interval_bonus,
            hp_interval_bonus=hp_interval_bonus,
            fever_bonus=fever_bonus,
            rank_bonus=rank_bonus,
            maya_gauge=maya_gauge,
            nextstage_bonus=nextstage_bonus,
            highest_health=highest_health,
            lowest_health=lowest_health,
            room_code=room_code,
            room_total_score=room_total_score,
            room_total_players=room_total_players,
        )


class ClientSongMapPayload(GameFormModel):
    clientSongMap: dict | list


class MultiplayerUpdatePayload(GameFormModel):
    token: int


class RoomInviteForm(GameFormModel):
    to: int

    @classmethod
    def as_form(cls, to: int = Form(...)):
        return cls(to=to)


class RoomStatusForm(GameFormModel):
    shareToken: str

    @classmethod
    def as_form(cls, shareToken: str = Form(...)):
        return cls(shareToken=shareToken)
