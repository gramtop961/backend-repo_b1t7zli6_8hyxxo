"""
Database Schemas for EcoTrail Gear

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name by convention in this environment.
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, HttpUrl


class Impactstats(BaseModel):
    """Aggregated impact metrics displayed on the homepage."""
    trees_planted: int = Field(0, ge=0)
    bottles_recycled: int = Field(0, ge=0)
    carbon_offset_kg: float = Field(0.0, ge=0)


class Product(BaseModel):
    """Product catalog items."""
    title: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category: str = Field(..., description="Primary category")
    subcategories: List[str] = Field(default_factory=list)
    activity_types: List[str] = Field(default_factory=list, description="e.g., backpacking, mountaineering")
    seasons: List[str] = Field(default_factory=list, description="e.g., spring/summer, fall/winter, all-season")
    sustainability_features: List[str] = Field(default_factory=list)
    special_features: List[str] = Field(default_factory=list)
    images: List[HttpUrl] = Field(default_factory=list)
    price: float = Field(..., ge=0)
    sale_price: Optional[float] = Field(None, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    rating: float = Field(0, ge=0, le=5)
    review_count: int = Field(0, ge=0)
    in_stock: bool = True
    availability: str = Field("in stock", description="in stock | pre-order | backorder")
    eco_badge: Optional[str] = Field(None, description="Primary sustainable attribute badge text")
    specs: Dict[str, str] = Field(default_factory=dict, description="Technical specifications")


class Review(BaseModel):
    """Multidimensional customer review."""
    product_id: str
    title: str
    body: str
    photos: List[HttpUrl] = Field(default_factory=list)
    videos: List[HttpUrl] = Field(default_factory=list)
    verified_purchase: bool = False
    days_tested: Optional[int] = Field(None, ge=0)
    ratings: Dict[str, int] = Field(default_factory=dict, description="keys: durability, comfort, weather_resistance, value, sustainability, performance (1-5)")
    activity_used: Optional[str] = None
    season_tested: Optional[str] = None
    experience_level: Optional[str] = None
    variant: Optional[str] = None
    author_name: Optional[str] = None


class User(BaseModel):
    name: str
    email: str
    is_active: bool = True
