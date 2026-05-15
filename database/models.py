from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Job:
    source: str
    company: str
    title: str
    location: str
    url: str
    description: str = ""
    ats_job_id: Optional[str] = None
    fit_score: int = 0
    status: str = "discovered"
    id: Optional[int] = None
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    application_packet_path: Optional[str] = None
    generated_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class Candidate:
    first_name: str
    last_name: str
    email: str
    phone: str = ""

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self):
        data = asdict(self)
        data["name"] = self.name
        return data


@dataclass
class ApplicationPacket:
    job_id: int
    resume_path: str
    cover_letter_path: str
    application_packet_path: str

    def to_dict(self):
        return asdict(self)
