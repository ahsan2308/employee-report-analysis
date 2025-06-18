from pydantic import BaseModel
from typing import List, Dict, Any, Union, Optional

class TrendMetadata(BaseModel):
    """Metadata associated with a trend dataset."""
    min: float
    max: float
    avg: float

class TrendDataset(BaseModel):
    """Represents a single dataset within a trend visualization."""
    label: str
    data: List[Union[float, int, None]]
    metadata: TrendMetadata
    # Add optional color fields for multi-criteria visualization
    backgroundColor: Optional[str] = None
    borderColor: Optional[str] = None


class TrendResponse(BaseModel):
    """
    Response model for trend visualization data.
    Used for both single criterion (like sentiment) and multi-criteria visualizations.
    """
    labels: List[str]
    datasets: List[TrendDataset]

# For backward compatibility, keep SentimentTrendResponse as an alias
SentimentTrendResponse = TrendResponse

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
