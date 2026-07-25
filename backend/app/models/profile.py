from pydantic import BaseModel


class Experience(BaseModel):
    title: str
    organization: str
    start_date: str
    end_date: str | None = None
    highlights: list[str] = []


class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = []
    link: str | None = None


class Profile(BaseModel):
    name: str
    summary: str
    skills: list[str] = []
    experience: list[Experience] = []
    projects: list[Project] = []
    education: list[str] = []
