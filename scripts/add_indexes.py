import sqlite3

def add_indexes():
    """添加索引以优化查询性能"""
    try:
        conn = sqlite3.connect('./db/bilibili_mall.db')
        cursor = conn.cursor()
        
        # 创建索引的SQL语句列表
        indexes = [
            # SKU表索引
            "CREATE INDEX IF NOT EXISTS idx_skus_name ON skus(name)",
            
            # 商品表索引
            "CREATE INDEX IF NOT EXISTS idx_c2c_items_sku_brand ON c2c_items(sku_id, brand_id)",
            "CREATE INDEX IF NOT EXISTS idx_c2c_items_price ON c2c_items(price)",
            "CREATE INDEX IF NOT EXISTS idx_c2c_items_items_id ON c2c_items(items_id)",
            
            # 品牌表索引
            "CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(name)",
            
            # 复合索引
            "CREATE INDEX IF NOT EXISTS idx_items_sku_price ON c2c_items(sku_id, price)",
            "CREATE INDEX IF NOT EXISTS idx_items_brand_price ON c2c_items(brand_id, price)",
        ]
        
        print("开始创建索引...")
        for idx, sql in enumerate(indexes, 1):
            try:
                print(f"[{idx}/{len(indexes)}] 执行: {sql}")
                cursor.execute(sql)
                print("✓ 成功")
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    print("! 索引已存在，跳过")
                else:
                    print(f"× 失败: {e}")
            except Exception as e:
                print(f"× 失败: {e}")
        
        # 提交更改
        conn.commit()
        print("\n索引创建完成!")
        
        # 分析数据库以优化查询计划
        print("\n开始分析数据库...")
        cursor.execute("ANALYZE")
        print("数据库分析完成!")
        
    except Exception as e:
        print(f"发生错误: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_indexes() 