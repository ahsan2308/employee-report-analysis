"""
Pydantic models for structured data responses.

This module contains all the Pydantic models used for structured data
generation with LLM services. Import these models when you need to
define a structured output format for LLM responses.
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Achievement(BaseModel):
    """Model representing an employee achievement."""
    description: str = Field(
        description="Detailed description of the achievement"
    )
    impact: str = Field(
        description="The measurable impact or result of this achievement"
    )


class Challenge(BaseModel):
    """Model representing a challenge faced by an employee."""
    description: str = Field(
        description="Detailed description of the challenge faced"
    )
    severity: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="How severe the challenge is (low, medium, high)"
    )


class EmployeeAnalysis(BaseModel):
    """Model for comprehensive employee report analysis."""
    achievements: List[Achievement] = Field(
        description="Key achievements mentioned in the report"
    )
    challenges: List[Challenge] = Field(
        description="Challenges mentioned in the report"
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the report"
    )
    topics: List[str] = Field(
        description="Key topics covered in the report"
    )
    action_items: List[str] = Field(
        description="Recommended action items based on the report"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Overall risk assessment level"
    )
    risk_explanation: str = Field(
        description="Explanation for the assigned risk level"
    )


class ContactInfo(BaseModel):
    """Model for contact information."""
    email: str = Field(description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")


class PersonInfo(BaseModel):
    """Model for basic person information."""
    name: str = Field(description="Full name of the person")
    age: int = Field(description="Age in years")
    occupation: str = Field(description="Current occupation or job title")
    skills: List[str] = Field(description="List of professional skills")
    contact: Optional[ContactInfo] = None


class Project(BaseModel):
    """Model for project information."""
    name: str = Field(description="Project name")
    description: str = Field(description="Project description")
    status: Literal["planned", "in_progress", "completed"] = Field(
        default="in_progress",
        description="Current status of the project"
    )
    duration_months: Optional[int] = Field(
        None, description="Duration in months (if applicable)"
    )


class DeveloperProfile(BaseModel):
    """Model for a full developer profile."""
    person: PersonInfo
    projects: List[Project] = Field(description="List of projects")
    years_experience: int = Field(description="Years of professional experience")
    specialization: str = Field(description="Area of specialization")
    languages: List[str] = Field(description="Programming languages known")
    frameworks: List[str] = Field(description="Frameworks and tools known")


class Pet(BaseModel):
    """Model for pet information."""
    name: str = Field(description="Pet's name")
    animal: str = Field(description="Type of animal (e.g., dog, cat)")
    age: int = Field(description="Age in years")
    color: Optional[str] = Field(None, description="Color of the pet")
    favorite_toy: Optional[str] = Field(None, description="Pet's favorite toy")


class PetList(BaseModel):
    """Model for a list of pets."""
    pets: List[Pet] = Field(description="List of pets")


# You can add more models as needed for your application
