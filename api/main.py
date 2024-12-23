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
DATABASE_URL = "./db/bilibili_mall.db"

def get_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

# 在初始化数据库连接后添加黑名单表创建代码
def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 创建黑名单表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        uname TEXT NOT NULL,
        reason TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(uid)
    )
    ''')
    
    conn.commit()
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
    created_at: datetime
    is_blacklisted: bool

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
async def get_skus(
    page: int = 1, 
    page_size: int = 20, 
    brand_id: Optional[int] = None, 
    keyword: Optional[str] = None, 
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "desc"
):
    """获取SKU列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 构建查询条件
        params = []
        brand_filter = ""
        if brand_id is not None:
            brand_filter = "AND i.brand_id = ?"
            params.append(brand_id)
        
        # 添加搜索参数
        search_term = f"%{keyword}%" if keyword else None
        params.extend([search_term, search_term])  # 两次，因为有两个查询都用到了
        
        # 构建排序条件
        order_clause = "s.sku_id DESC"
        if sort_by:
            order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
            if sort_by == "min_price":
                order_clause = f"min_price {order_direction}"
            elif sort_by == "total_items":
                order_clause = f"total_items {order_direction}"
        
        # 主查询
        query = f"""
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
                    COUNT(fi.id) as total_items,
                    MAX(fi.id) as latest_id
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
            ORDER BY {
                'latest_id DESC' if not sort_by
                else f"total_items {order_direction}" if sort_by == 'total_items'
                else f"min_price {order_direction}" if sort_by == 'min_price'
                else 'latest_id DESC'
            }
            LIMIT ? OFFSET ?
        """
        
        # 添加分页参数
        params.extend([page_size, (page - 1) * page_size])
        
        # 执行查询
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
            "total": cursor.rowcount,
            "page": page,
            "page_size": page_size,
            "total_pages": (cursor.rowcount + page_size - 1) // page_size
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
                i.publish_status,
                i.created_at,
                i.is_blacklisted
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
            elif avatar_url.startswith('//'):
                avatar_url = f"https:{avatar_url}"
            
            # 只有当URL不包含 /bfs/ 时才添加
            if '/bfs/' not in avatar_url:
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
                "publish_status": row['publish_status'],
                "created_at": row['created_at'],
                "is_blacklisted": row['is_blacklisted']
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
async def get_status_changes(page: int = 1, page_size: int = 20, status: str = 'all'):
    """获取最近状态发生变更的商品"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 构建状态过滤条件
        status_condition = "AND c.publish_status != 1"  # 默认排除在售商品
        if status == 'sold':
            status_condition = "AND c.publish_status = -2"
        elif status == 'offline':
            status_condition = "AND c.publish_status = -1"
        
        # 获取过滤后的总记录数
        cursor.execute(f"""
            WITH filtered_items AS (
                SELECT DISTINCT c.id
                FROM c2c_items c
                JOIN skus s ON c.sku_id = s.sku_id
                WHERE c.last_check_time >= datetime('now', '-24 hours')
                {status_condition}
            )
            SELECT COUNT(*) as total FROM filtered_items
        """)
        total = cursor.fetchone()['total']
        
        # 计算分页
        offset = (page - 1) * page_size
        
        # 获取分页数据，添加用户信息
        cursor.execute(f"""
            SELECT DISTINCT
                c.id,
                s.sku_id,
                s.name,
                s.img,
                c.price,
                c.publish_status,
                datetime(c.last_check_time, '+8 hours') as last_check_time,
                c.uname as seller_name,
                c.uid as seller_uid,
                c.uspace_jump_url as seller_url
            FROM c2c_items c
            JOIN skus s ON c.sku_id = s.sku_id
            WHERE c.last_check_time >= datetime('now', '-24 hours')
            {status_condition}
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

@app.get("/api/blacklist")
async def get_blacklist(page: int = 1, page_size: int = 20):
    """获取黑名单用户列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute("SELECT COUNT(*) as total FROM blacklist")
        total = cursor.fetchone()['total']
        
        # 计算分页
        offset = (page - 1) * page_size
        
        # 获取分页数据
        cursor.execute("""
            SELECT 
                b.*,
                (
                    SELECT COUNT(DISTINCT c.id)
                    FROM c2c_items c
                    WHERE c.uid = b.uid
                ) as total_items
            FROM blacklist b
            ORDER BY b.created_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row['id'],
                "uid": row['uid'],
                "uname": row['uname'],
                "reason": row['reason'],
                "created_at": row['created_at'],
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

@app.get("/api/suspicious-users")
async def get_suspicious_users():
    """获取可疑用户列表
    1. 1小时内对同一商品上架超过20次的用户
    2. 1小时内对3个以上SKU上架超过10次的用户
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            WITH single_sku_stats AS (
                SELECT 
                    c.uid,
                    c.uname,
                    c.sku_id,
                    COUNT(*) as listing_count,
                    MIN(c.created_at) as first_listing,
                    MAX(c.created_at) as last_listing
                FROM c2c_items c
                WHERE c.created_at >= datetime('now', '-1 hour')
                GROUP BY c.uid, c.uname, c.sku_id
                HAVING listing_count >= 20
            ),
            multi_sku_stats AS (
                SELECT 
                    c.uid,
                    c.uname,
                    COUNT(DISTINCT c.sku_id) as sku_count,
                    MIN(c.created_at) as first_listing,
                    MAX(c.created_at) as last_listing
                FROM c2c_items c
                WHERE c.created_at >= datetime('now', '-1 hour')
                GROUP BY c.uid, c.uname
                HAVING sku_count >= 3
                AND (
                    SELECT COUNT(*)
                    FROM c2c_items c2
                    WHERE c2.uid = c.uid
                    AND c2.created_at >= datetime('now', '-1 hour')
                ) >= (sku_count * 10)
            )
            SELECT 
                us.uid,
                us.uname,
                us.sku_id,
                s.name as sku_name,
                us.listing_count,
                us.first_listing,
                us.last_listing,
                (
                    SELECT COUNT(DISTINCT c2.sku_id)
                    FROM c2c_items c2
                    WHERE c2.uid = us.uid
                ) as total_skus
            FROM single_sku_stats us
            JOIN skus s ON us.sku_id = s.sku_id
            WHERE NOT EXISTS (
                SELECT 1 FROM blacklist b 
                WHERE b.uid = us.uid
            )
            UNION ALL
            SELECT 
                ms.uid,
                ms.uname,
                NULL as sku_id,
                '多个商品' as sku_name,
                (
                    SELECT COUNT(*)
                    FROM c2c_items c2
                    WHERE c2.uid = ms.uid
                    AND c2.created_at >= datetime('now', '-1 hour')
                ) as listing_count,
                ms.first_listing,
                ms.last_listing,
                ms.sku_count as total_skus
            FROM multi_sku_stats ms
            WHERE NOT EXISTS (
                SELECT 1 FROM blacklist b 
                WHERE b.uid = ms.uid
            )
            ORDER BY listing_count DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "uid": row['uid'],
                "uname": row['uname'],
                "sku_id": row['sku_id'],
                "sku_name": row['sku_name'],
                "listing_count": row['listing_count'],
                "first_listing": row['first_listing'],
                "last_listing": row['last_listing'],
                "total_skus": row['total_skus']
            })
        
        return results
    finally:
        conn.close()

@app.post("/api/blacklist")
async def add_to_blacklist(user: dict):
    """添加用户到黑名单"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # 添加到黑名单
            cursor.execute("""
                INSERT INTO blacklist (uid, uname, reason)
                VALUES (?, ?, ?)
            """, (user['uid'], user['uname'], user['reason']))
            
            # 更新该用户所有商品的状态为-1
            cursor.execute("""
                UPDATE c2c_items 
                SET publish_status = -1,
                    is_blacklisted = 1,
                    last_check_time = CURRENT_TIMESTAMP
                WHERE uid = ?
            """, (user['uid'],))
            
            cursor.execute("COMMIT")
            
            return {
                "success": True,
                "message": "已添加到黑名单"
            }
            
        except sqlite3.IntegrityError:
            cursor.execute("ROLLBACK")
            return {
                "success": False,
                "message": "该用户已在黑名单中"
            }
            
        except Exception as e:
            cursor.execute("ROLLBACK")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        conn.close()

@app.delete("/api/blacklist/{uid}")
async def remove_from_blacklist(uid: str):
    """从黑名单中移除用户"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM blacklist WHERE uid = ?", (uid,))
        conn.commit()
        
        return {
            "success": True,
            "message": "已从黑名单中移除"
        }
    finally:
        conn.close()

@app.get("/api/user-stats")
async def get_user_stats():
    """获取用户行为统计数据"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 定义时间段
        periods = [
            ('1小时', 'datetime("now", "-1 hour")'),
            ('3小时', 'datetime("now", "-3 hours")'),
            ('12小时', 'datetime("now", "-12 hours")'),
            ('24小时', 'datetime("now", "-24 hours")')
        ]
        
        results = {}
        
        for period_name, period_sql in periods:
            # 获取每个时间段内用户的上架数据
            cursor.execute(f"""
                WITH user_stats AS (
                    SELECT 
                        c.uid,
                        c.uname,
                        COUNT(DISTINCT c.id) as listing_count,
                        COUNT(DISTINCT c.sku_id) as sku_count,
                        MIN(c.price) as min_price,
                        MAX(c.price) as max_price,
                        MIN(c.created_at) as first_listing,
                        MAX(c.created_at) as last_listing,
                        (
                            SELECT b.reason 
                            FROM blacklist b 
                            WHERE b.uid = c.uid
                            LIMIT 1
                        ) as blacklist_reason
                    FROM c2c_items c
                    WHERE c.created_at >= {period_sql}
                    GROUP BY c.uid, c.uname
                )
                SELECT 
                    us.*,
                    CASE 
                        WHEN blacklist_reason IS NOT NULL THEN 1
                        ELSE 0
                    END as is_blacklisted
                FROM user_stats us
                ORDER BY us.listing_count DESC
                LIMIT 50
            """)
            
            period_results = []
            for row in cursor.fetchall():
                period_results.append({
                    "uid": row['uid'],
                    "uname": row['uname'],
                    "listing_count": row['listing_count'],
                    "sku_count": row['sku_count'],
                    "min_price": float(row['min_price']),
                    "max_price": float(row['max_price']),
                    "first_listing": row['first_listing'],
                    "last_listing": row['last_listing'],
                    "is_blacklisted": row['is_blacklisted'],
                    "blacklist_reason": row['blacklist_reason']
                })
            
            results[period_name] = period_results
        
        return results
    finally:
        conn.close()

@app.get("/api/user/items")
async def get_user_items(uid: str, uname: str):
    """获取指定用户的所有商品"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT
                s.sku_id,
                s.name,
                s.img,
                s.market_price,
                COUNT(DISTINCT c.id) as listing_count,
                MIN(c.price) as min_price,
                MAX(c.price) as max_price,
                MIN(c.created_at) as first_listing,
                MAX(c.created_at) as last_listing
            FROM c2c_items c
            JOIN skus s ON c.sku_id = s.sku_id
            WHERE c.uid = ? AND c.uname = ?
            GROUP BY s.sku_id, s.name, s.img, s.market_price
            ORDER BY last_listing DESC
        """, (uid, uname))
        
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
            
            results.append({
                "sku_id": row['sku_id'],
                "name": row['name'],
                "img": img_url,
                "market_price": float(row['market_price']),
                "listing_count": row['listing_count'],
                "min_price": float(row['min_price']),
                "max_price": float(row['max_price']),
                "first_listing": row['first_listing'],
                "last_listing": row['last_listing']
            })
        
        return results
    finally:
        conn.close()

@app.get("/api/statistics")
async def get_statistics():
    """获取统计数据"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 定义时间段
        periods = [
            ('1小时', 'datetime("now", "-1 hour")'),
            ('3小时', 'datetime("now", "-3 hours")'),
            ('6小时', 'datetime("now", "-6 hours")'),
            ('12小时', 'datetime("now", "-12 hours")'),
            ('24小时', 'datetime("now", "-24 hours")')
        ]
        
        results = {}
        
        for period_name, period_sql in periods:
            # 新增商品数量
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM c2c_items
                WHERE created_at >= {period_sql}
            """)
            new_items = cursor.fetchone()['count']
            
            # 新增SKU数量
            cursor.execute(f"""
                SELECT COUNT(DISTINCT sku_id) as count
                FROM c2c_items
                WHERE created_at >= {period_sql}
            """)
            new_skus = cursor.fetchone()['count']
            
            # 新增封禁用户数量
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM blacklist
                WHERE created_at >= {period_sql}
            """)
            new_blacklist = cursor.fetchone()['count']
            
            # 已售商品数量
            cursor.execute(f"""
                SELECT COUNT(*) as count
                FROM c2c_items
                WHERE publish_status = -2
                AND last_check_time >= {period_sql}
            """)
            sold_items = cursor.fetchone()['count']
            
            # 获取最活跃用户
            cursor.execute(f"""
                SELECT 
                    uid,
                    uname,
                    COUNT(*) as listing_count,
                    COUNT(DISTINCT sku_id) as sku_count,
                    MIN(created_at) as first_listing,
                    MAX(created_at) as last_listing,
                    (
                        SELECT reason 
                        FROM blacklist b 
                        WHERE b.uid = c.uid
                        LIMIT 1
                    ) as blacklist_reason
                FROM c2c_items c
                WHERE created_at >= {period_sql}
                GROUP BY uid, uname
                ORDER BY listing_count DESC
                LIMIT 5
            """)
            
            active_users = []
            for row in cursor.fetchall():
                active_users.append({
                    "uid": row['uid'],
                    "uname": row['uname'],
                    "listing_count": row['listing_count'],
                    "sku_count": row['sku_count'],
                    "first_listing": row['first_listing'],
                    "last_listing": row['last_listing'],
                    "is_blacklisted": row['blacklist_reason'] is not None,
                    "blacklist_reason": row['blacklist_reason']
                })
            
            results[period_name] = {
                "new_items": new_items,
                "new_skus": new_skus,
                "new_blacklist": new_blacklist,
                "sold_items": sold_items,
                "active_users": active_users
            }
        
        return results
    finally:
        conn.close()

@app.get("/api/statistics/trend")
async def get_statistics_trend():
    """获取最近一小时的趋势数据（按分钟）"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 获取最近60分钟的数据
        cursor.execute("""
            WITH RECURSIVE 
            minutes(minute) AS (
                SELECT datetime('now', '-59 minutes')
                UNION ALL
                SELECT datetime(minute, '+1 minutes')
                FROM minutes
                WHERE minute < datetime('now')
            )
            SELECT 
                strftime('%H:%M', datetime(m.minute, '+8 hours')) as time,
                COUNT(c.id) as items_count,
                COUNT(DISTINCT c.sku_id) as skus_count,
                COUNT(DISTINCT c.uid) as users_count
            FROM minutes m
            LEFT JOIN c2c_items c ON 
                strftime('%Y-%m-%d %H:%M', c.created_at) = strftime('%Y-%m-%d %H:%M', datetime(m.minute))
            GROUP BY m.minute
            ORDER BY m.minute
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "time": row['time'],
                "items_count": row['items_count'],
                "skus_count": row['skus_count'],
                "users_count": row['users_count']
            })
        
        return results
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 