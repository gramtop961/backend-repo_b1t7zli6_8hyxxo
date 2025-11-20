import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Product as ProductModel, Review as ReviewModel, Impactstats as ImpactModel

app = FastAPI(title="EcoTrail Gear API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "EcoTrail Gear API is running"}


# -------- Impact Stats --------
class ImpactResponse(BaseModel):
    trees_planted: int
    bottles_recycled: int
    carbon_offset_kg: float


@app.get("/api/impact", response_model=ImpactResponse)
def get_impact():
    try:
        docs = get_documents("impactstats", {}, limit=1)
        if docs:
            doc = docs[0]
            return ImpactResponse(
                trees_planted=int(doc.get("trees_planted", 0)),
                bottles_recycled=int(doc.get("bottles_recycled", 0)),
                carbon_offset_kg=float(doc.get("carbon_offset_kg", 0.0)),
            )
    except Exception:
        pass
    # Fallback demo values
    return ImpactResponse(trees_planted=128450, bottles_recycled=9723450, carbon_offset_kg=654321.5)


# -------- Products --------
class ProductCreate(ProductModel):
    pass


class ProductListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


@app.post("/api/products", status_code=201)
def create_product(product: ProductCreate):
    try:
        product_id = create_document("product", product)
        return {"id": product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products", response_model=ProductListResponse)
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    activity: Optional[str] = None,
    season: Optional[str] = None,
    sustainable: Optional[str] = Query(None, description="sustainability feature filter"),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: Optional[str] = Query("relevance", enum=[
        "relevance", "price_asc", "price_desc", "newest", "best_sellers", "highest_rated", "most_sustainable"
    ]),
    page: int = 1,
    page_size: int = 12,
):
    filter_q: Dict[str, Any] = {}

    if q:
        # simple case-insensitive search on title/description
        filter_q["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filter_q["category"] = category
    if activity:
        filter_q["activity_types"] = {"$in": [activity]}
    if season:
        filter_q["seasons"] = {"$in": [season]}
    if sustainable:
        filter_q["sustainability_features"] = {"$in": [sustainable]}
    if min_price is not None or max_price is not None:
        price_filter: Dict[str, Any] = {}
        if min_price is not None:
            price_filter["$gte"] = min_price
        if max_price is not None:
            price_filter["$lte"] = max_price
        filter_q["price"] = price_filter

    # Sorting mapping
    sort_spec = None
    if sort == "price_asc":
        sort_spec = [("price", 1)]
    elif sort == "price_desc":
        sort_spec = [("price", -1)]
    elif sort == "highest_rated":
        sort_spec = [("rating", -1)]

    try:
        collection = db["product"] if db else None
        if collection is None:
            # Demo fallback items when DB not available
            demo_items = [
                {
                    "id": "demo-1",
                    "title": "Evergreen Ultralight Tent",
                    "price": 349.0,
                    "sale_price": 299.0,
                    "currency": "USD",
                    "category": "Carbon-Neutral Camping Equipment",
                    "images": [
                        "https://images.unsplash.com/photo-1501706362039-c06b2d715385?q=80&w=1200&auto=format&fit=crop",
                        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1200&auto=format&fit=crop",
                    ],
                    "rating": 4.7,
                    "review_count": 126,
                    "eco_badge": "Carbon Neutral",
                    "sustainability_features": ["carbon-neutral", "recycled"],
                },
                {
                    "id": "demo-2",
                    "title": "TrailWave Recycled Fleece",
                    "price": 129.0,
                    "sale_price": None,
                    "currency": "USD",
                    "category": "Recycled Material Hiking Gear",
                    "images": [
                        "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?q=80&w=1200&auto=format&fit=crop",
                        "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?q=80&w=1200&auto=format&fit=crop",
                    ],
                    "rating": 4.5,
                    "review_count": 342,
                    "eco_badge": "Recycled Materials",
                    "sustainability_features": ["recycled"],
                },
                {
                    "id": "demo-3",
                    "title": "SunSpark Solar Charger",
                    "price": 99.0,
                    "sale_price": 89.0,
                    "currency": "USD",
                    "category": "Renewable Energy Outdoor Accessories",
                    "images": [
                        "https://images.unsplash.com/photo-1500534315581-c1f6f8a91b9b?q=80&w=1200&auto=format&fit=crop",
                        "https://images.unsplash.com/photo-1469474968028-56623f02e42e?q=80&w=1200&auto=format&fit=crop",
                    ],
                    "rating": 4.2,
                    "review_count": 88,
                    "eco_badge": "Renewable Energy",
                    "sustainability_features": ["renewable"],
                },
            ]
            # Simple paging simulation
            start = (page - 1) * page_size
            end = start + page_size
            return ProductListResponse(items=demo_items[start:end], total=len(demo_items), page=page, page_size=page_size)

        # DB-backed
        cursor = collection.find(filter_q)
        if sort_spec:
            cursor = cursor.sort(sort_spec)
        total = collection.count_documents(filter_q)
        cursor = cursor.skip((page - 1) * page_size).limit(page_size)
        items = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            items.append(doc)
        return ProductListResponse(items=items, total=total, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------- Reviews --------
class ReviewCreate(ReviewModel):
    pass


@app.post("/api/reviews", status_code=201)
def create_review(review: ReviewCreate):
    try:
        review_id = create_document("review", review)
        return {"id": review_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviews/{product_id}")
def get_reviews(product_id: str, min_rating: Optional[int] = None):
    try:
        filter_q: Dict[str, Any] = {"product_id": product_id}
        if min_rating is not None:
            filter_q["ratings.sustainability"] = {"$gte": min_rating}
        items = get_documents("review", filter_q)
        for item in items:
            item["id"] = str(item.pop("_id", ""))
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
