import sqlite3

def clean_empty_brands():
    """删除没有关联商品的品牌"""
    try:
        conn = sqlite3.connect('./db/bilibili_mall.db')
        cursor = conn.cursor()
        
        print("开始检查空品牌...")
        
        # 查找没有关联商品的品牌
        cursor.execute('''
            SELECT b.id, b.name, b.keywords
            FROM brands b
            LEFT JOIN c2c_items i ON b.id = i.brand_id
            GROUP BY b.id, b.name, b.keywords
            HAVING COUNT(i.id) = 0
        ''')
        
        empty_brands = cursor.fetchall()
        
        if not empty_brands:
            print("没有找到空品牌，无需清理")
            return
        
        print(f"\n找到 {len(empty_brands)} 个空品牌:")
        for brand_id, name, keywords in empty_brands:
            print(f"- ID: {brand_id}, 名称: {name}, 关键词: {keywords}")
        
        # 确认是否继续
        confirm = input("\n是否删除这些空品牌？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
        
        # 开始事务
        cursor.execute("BEGIN")
        
        try:
            # 删除空品牌
            cursor.execute('''
                DELETE FROM brands
                WHERE id IN (
                    SELECT b.id
                    FROM brands b
                    LEFT JOIN c2c_items i ON b.id = i.brand_id
                    GROUP BY b.id
                    HAVING COUNT(i.id) = 0
                )
            ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"\n清理完成!")
            print(f"- 删除了 {deleted_count} 个空品牌")
            
        except Exception as e:
            conn.rollback()
            print(f"发生错误: {e}")
            raise
            
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    clean_empty_brands() 