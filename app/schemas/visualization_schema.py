from pydantic import BaseModel
from typing import List, Dict, Any, Union

class TrendMetadata(BaseModel):
    """Metadata associated with a trend dataset."""
    min: float
    max: float
    avg: float

class TrendDataset(BaseModel):
    """Represents a single dataset within a trend visualization."""
    label: str
    data: List[Union[float, int]]
    metadata: TrendMetadata

class SentimentTrendResponse(BaseModel):
    """Response model for sentiment trend visualization data."""
    labels: List[str]
    datasets: List[TrendDataset]

# Add other visualization response schemas here as needed
