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

# Heatmap-related models
class HeatmapCell(BaseModel):
    """Represents a single cell in a heatmap."""
    x: int  # X coordinate/index  
    y: int  # Y coordinate/index
    value: float  # Value determining cell color

class HeatmapMetadata(BaseModel):
    """Metadata associated with a heatmap."""
    min: float
    max: float
    avg: float

class HeatmapResponse(BaseModel):
    """Response model for heatmap visualization data."""
    x_labels: List[str]  # Labels for x-axis (e.g., time periods)
    y_labels: List[str]  # Labels for y-axis (e.g., employees, departments)
    cells: List[HeatmapCell]  # Cell data
    metadata: HeatmapMetadata  # Metadata like min, max, avg values
