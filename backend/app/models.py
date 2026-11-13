from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionRequest(StrictModel):
    profile_id: str = Field(min_length=1, max_length=100)
    locale: str = Field(min_length=2, max_length=35)


class VehicleContext(StrictModel):
    property_id: Literal["door.position", "ev.battery_soc", "fuel.percent", "tire.low_pressure", "safety.telltales"]
    area_id: str | None = Field(default=None, max_length=50)
    value: str | int | bool | None = None
    read_status: Literal["NOT_REQUESTED", "LOADING", "VALUE", "UNAVAILABLE", "ERROR", "STALE"]
    received_at: str | None = None
    source: Literal["MOCK", "PLEOS"]

    @model_validator(mode="after")
    def consistent_value(self):
        if (self.read_status == "VALUE") != (self.value is not None):
            raise ValueError("VALUE requires a value; all other statuses require null")
        return self


class GuideContext(StrictModel):
    guide_id: str | None = None
    step_id: str | None = None


class AskRequest(SessionRequest):
    request_id: str = Field(min_length=1, max_length=100)
    session_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    guide_context: GuideContext = Field(default_factory=GuideContext)
    vehicle_context: list[VehicleContext] = Field(default_factory=list, max_length=5)


class TranslateRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=100)
    session_id: str
    profile_id: str
    source_locale: str = "auto"
    target_locale: str
    text: str = Field(min_length=1, max_length=3000)
    content_kind: Literal["QUESTION", "ANSWER", "GUIDE"]
    guide_id: str | None = None


class ModelAnswer(StrictModel):
    status: Literal["ANSWERED", "NEED_MORE_INFO", "NO_RELIABLE_SOURCE"]
    answer: str = Field(min_length=1, max_length=4000)
    source_ids: list[str] = Field(max_length=5)
    follow_up_question: str | None


class ModelTranslation(StrictModel):
    source_locale: str
    translated_text: str = Field(min_length=1, max_length=6000)
