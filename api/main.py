from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

app = FastAPI(title="B站商城API")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库连接
DATABASE_URL = "bilibili_mall.db"

def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

# 模型定义
class SkuInfo(BaseModel):
    sku_id: int
    name: str
    img: str
    market_price: float
    price_range: dict
    total_items: int

class ItemDetail(BaseModel):
    c2c_items_id: int
    seller_name: str
    seller_uid: str | None = None
    seller_avatar: str | None = None
    seller_url: str | None = None
    price: float
    market_price: float
    url: str

class SkuListResponse(BaseModel):
    items: List[SkuInfo]
    total: int
    page: int
    page_size: int
    total_pages: int

@app.get("/api/brands", response_model=List[dict])
async def get_brands():
    """获取所有品牌列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                b.id,
                b.name,
                COUNT(DISTINCT s.sku_id) as total_items
            FROM brands b
            LEFT JOIN c2c_items c ON b.id = c.brand_id
            LEFT JOIN skus s ON s.sku_id = c.sku_id
            GROUP BY b.id, b.name
            ORDER BY total_items DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

@app.get("/api/skus", response_model=SkuListResponse)
async def get_sku_list(
    brand_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """获取SKU列表及其价格范围"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 先获取总数
        count_query = """
            SELECT COUNT(DISTINCT s.sku_id) as total
            FROM skus s
            WHERE EXISTS (
                SELECT 1 
                FROM c2c_items i 
                WHERE i.sku_id = s.sku_id
                {brand_filter}
            )
            AND (? IS NULL OR s.name LIKE ?)
        """
        
        # 主查询
        base_query = """
            WITH sku_stats AS (
                SELECT 
                    s.sku_id,
                    s.name,
                    s.img,
                    s.market_price,
                    MIN(i.price) as min_price,
                    MAX(i.price) as max_price,
                    COUNT(i.id) as total_items
                FROM skus s
                JOIN c2c_items i ON i.sku_id = s.sku_id
                WHERE 1=1
                {brand_filter}
                AND (? IS NULL OR s.name LIKE ?)
                GROUP BY s.sku_id, s.name, s.img, s.market_price
            )
            SELECT 
                sku_id,
                name,
                img,
                market_price,
                min_price,
                max_price,
                total_items
            FROM sku_stats
            ORDER BY total_items DESC
            LIMIT ? OFFSET ?
        """
        
        # 准备查询参数
        params = []
        brand_filter = ""
        if brand_id is not None:
            brand_filter = "AND i.brand_id = ?"
            params.append(brand_id)
        
        # 添加搜索参数
        search_term = f"%{keyword}%" if keyword else None
        count_params = params.copy()  # 为计数查询创建参数副本
        count_params.extend([keyword, search_term])
        
        # 获取总数
        count_query = count_query.format(brand_filter=brand_filter)
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']
        
        # 添加主查询的参数
        params.extend([keyword, search_term])  # 添加搜索参数
        params.extend([page_size, (page - 1) * page_size])  # 添加分页参数
        query = base_query.format(brand_filter=brand_filter)
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            # 处理图片URL
            img_url = row['img']
            if img_url.startswith('//'):
                img_url = f"https:{img_url}"
            
            results.append({
                "sku_id": row['sku_id'],
                "name": row['name'],
                "img": img_url,
                "market_price": row['market_price'],
                "price_range": {
                    "min": row['min_price'],
                    "max": row['max_price']
                },
                "total_items": row['total_items']
            })
        
        return {
            "items": results,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    finally:
        conn.close()

@app.get("/api/sku/{sku_id}/items", response_model=List[ItemDetail])
async def get_sku_items(sku_id: int):
    """获取指定SKU的所有在售商品"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                i.id as c2c_items_id,
                i.uname as seller_name,
                i.uid as seller_uid,
                i.uface as seller_avatar,
                i.uspace_jump_url as seller_url,
                i.price,
                s.market_price
            FROM c2c_items i
            JOIN skus s ON i.sku_id = s.sku_id
            WHERE i.sku_id = ?
            ORDER BY i.price ASC
        """, (sku_id,))
        
        results = []
        base_url = "https://mall.bilibili.com/neul-next/index.html?page=magic-market_detail&noTitleBar=1&itemsId="
        
        for row in cursor.fetchall():
            # 处理头像URL，添加默认值处理
            avatar_url = row['seller_avatar']
            if not avatar_url:
                avatar_url = 'https://i0.hdslb.com/bfs/face/member/noface.jpg'
            
            # 处理头像URL
            if avatar_url.startswith('//'):
                avatar_url = f"https:{avatar_url}"
            
            # 将头像域名从 i[0-9].hdslb.com 替换为 i[0-9].hdslb.com/bfs
            avatar_url = avatar_url.replace('i0.hdslb.com', 'i0.hdslb.com/bfs')
            avatar_url = avatar_url.replace('i1.hdslb.com', 'i1.hdslb.com/bfs')
            avatar_url = avatar_url.replace('i2.hdslb.com', 'i2.hdslb.com/bfs')
            
            # 处理个人空间URL
            seller_url = row['seller_url']
            if seller_url and not seller_url.startswith('http'):
                seller_url = f"https://space.bilibili.com/{row['seller_uid']}"
            
            results.append({
                "c2c_items_id": row['c2c_items_id'],
                "seller_name": row['seller_name'],
                "seller_uid": row['seller_uid'],
                "seller_avatar": avatar_url,
                "seller_url": seller_url,
                "price": row['price'],
                "market_price": row['market_price'],
                "url": f"{base_url}{row['c2c_items_id']}"
            })
        
        return results
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 