from fastapi import FastAPI, HTTPException, Response, status
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
    publish_status: int

class SkuListResponse(BaseModel):
    items: List[SkuInfo]
    total: int
    page: int
    page_size: int
    total_pages: int

# 添加批量删除的请求模型
class BatchDeleteRequest(BaseModel):
    productIds: List[int]

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
    sort_by: Optional[str] = "total_items",
    page: int = 1,
    page_size: int = 100
):
    """获取SKU列表及其价格范围"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 先获取总数
        count_query = """
            SELECT COUNT(*) as total
            FROM (
                SELECT DISTINCT s.sku_id
                FROM skus s
                JOIN c2c_items i ON i.sku_id = s.sku_id
                WHERE 1=1
                {brand_filter}
                AND (? IS NULL OR s.name LIKE ?)
            )
        """
        
        # 修改排序逻辑
        order_by = {
            "total_items": "total_items DESC",
            "min_price": "min_price ASC"
        }.get(sort_by, "total_items DESC")
        
        # 主查询
        base_query = """
            WITH filtered_items AS (
                SELECT 
                    i.sku_id,
                    i.price,
                    i.id
                FROM c2c_items i
                WHERE 1=1
                {brand_filter}
            ),
            sku_stats AS (
                SELECT 
                    s.sku_id,
                    s.name,
                    s.img,
                    s.market_price,
                    MIN(fi.price) as min_price,
                    MAX(fi.price) as max_price,
                    COUNT(fi.id) as total_items
                FROM skus s
                JOIN filtered_items fi ON fi.sku_id = s.sku_id
                WHERE 1=1
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
            WHERE total_items > 0
            ORDER BY {order_by}
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
        query = base_query.format(
            brand_filter=brand_filter,
            order_by=order_by
        )
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
                s.market_price,
                i.publish_status
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
                "url": f"{base_url}{row['c2c_items_id']}",
                "publish_status": row['publish_status']
            })
        
        return results
    finally:
        conn.close()

@app.delete("/api/products/batch")
async def batch_delete_products(request: BatchDeleteRequest):
    """批量删除商品及其关联的SKU"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # 开启事务
            cursor.execute("BEGIN TRANSACTION")
            
            for product_id in request.productIds:
                # 1. 删除关联的SKU
                cursor.execute("""
                    DELETE FROM c2c_items 
                    WHERE sku_id IN (
                        SELECT sku_id 
                        FROM skus 
                        WHERE sku_id = ?
                    )
                """, (product_id,))
                
                # 2. 删除商品SKU
                cursor.execute("""
                    DELETE FROM skus 
                    WHERE sku_id = ?
                """, (product_id,))
            
            # 提交事务
            cursor.execute("COMMIT")
            
            return {
                "success": True,
                "message": "删除成功"
            }
            
        except Exception as e:
            # 如果出错，回滚事务
            cursor.execute("ROLLBACK")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        conn.close()

@app.delete("/api/products/{product_id}/skus")
async def delete_product_skus(product_id: int):
    """删除指定商品的所有SKU"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # 开启事务
            cursor.execute("BEGIN TRANSACTION")
            
            # 删除关联的SKU
            cursor.execute("""
                DELETE FROM c2c_items 
                WHERE sku_id = ?
            """, (product_id,))
            
            # 提交事务
            cursor.execute("COMMIT")
            
            return {
                "success": True,
                "message": "SKU删除成功"
            }
            
        except Exception as e:
            # 如果出错，回滚事务
            cursor.execute("ROLLBACK")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        conn.close()

@app.post("/api/brands")
async def create_brand(brand: dict):
    """创建新品牌"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # 插入新品牌
            cursor.execute("""
                INSERT INTO brands (name)
                VALUES (?)
            """, (brand['name'],))
            
            cursor.execute("COMMIT")
            
            return {
                "success": True,
                "message": "品牌添加成功"
            }
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    finally:
        conn.close()

@app.delete("/api/brands/{brand_id}")
async def delete_brand(brand_id: int):
    """删除品牌"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # 检查是否有关联的商品
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM skus s
                JOIN c2c_items c ON s.sku_id = c.sku_id
                WHERE c.brand_id = ?
            """, (brand_id,))
            
            if cursor.fetchone()['count'] > 0:
                cursor.execute("ROLLBACK")
                return {
                    "success": False,
                    "message": "该品牌下还有商品，不能删除"
                }
            
            # 删除品牌
            cursor.execute("""
                DELETE FROM brands
                WHERE id = ?
            """, (brand_id,))
            
            cursor.execute("COMMIT")
            
            return {
                "success": True,
                "message": "品牌删除成功"
            }
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
            
    finally:
        conn.close()

@app.get("/api/status-changes")
async def get_status_changes(page: int = 1, page_size: int = 20):
    """获取最近状态发生变更的商品"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute("""
            SELECT COUNT(DISTINCT c.id) as total
            FROM c2c_items c
            JOIN skus s ON c.sku_id = s.sku_id
            WHERE c.last_check_time >= datetime('now', '-24 hours')
                AND c.publish_status != 1
        """)
        total = cursor.fetchone()['total']
        
        # 计算分页
        offset = (page - 1) * page_size
        
        # 获取分页数据，添加用户信息
        cursor.execute("""
            SELECT DISTINCT
                c.id,
                s.sku_id,
                s.name,
                s.img,
                c.price,
                c.publish_status,
                c.last_check_time,
                c.uname as seller_name,
                c.uid as seller_uid,
                c.uspace_jump_url as seller_url
            FROM c2c_items c
            JOIN skus s ON c.sku_id = s.sku_id
            WHERE c.last_check_time >= datetime('now', '-24 hours')
                AND c.publish_status != 1
            ORDER BY c.last_check_time DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        
        results = []
        for row in cursor.fetchall():
            img_url = row['img']
            if img_url:
                if img_url.startswith('//'):
                    img_url = f"https:{img_url}"
                if '/bfs/' not in img_url:
                    img_url = img_url.replace('i0.hdslb.com', 'i0.hdslb.com/bfs')
                    img_url = img_url.replace('i1.hdslb.com', 'i1.hdslb.com/bfs')
                    img_url = img_url.replace('i2.hdslb.com', 'i2.hdslb.com/bfs')
                
            # 处理个人空间URL
            seller_url = row['seller_url']
            if seller_url and not seller_url.startswith('http'):
                seller_url = f"https://space.bilibili.com/{row['seller_uid']}"
                
            results.append({
                "id": row['id'],
                "sku_id": row['sku_id'],
                "name": row['name'],
                "img": img_url,
                "price": float(row['price']),
                "publish_status": row['publish_status'],
                "last_check_time": row['last_check_time'],
                "seller_name": row['seller_name'],
                "seller_uid": row['seller_uid'],
                "seller_url": seller_url
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 