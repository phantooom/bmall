import sqlite3
import re

def extract_brand_name(name):
    """从商品名称中提取品牌名"""
    # 移除特殊字符和多余空格
    name = re.sub(r'[【】\[\]（）()]', ' ', name)
    name = ' '.join(name.split())
    
    # 获取第一个空格前的内容作为品牌名
    parts = name.split(' ', 1)
    if parts:
        return parts[0].strip().upper()  # 转为大写以便统一处理
    return None

def update_brands():
    """更新品牌数据"""
    try:
        conn = sqlite3.connect('bilibili_mall.db')
        cursor = conn.cursor()
        
        print("开始处理品牌数据...")
        
        # 获取所有商品名称
        cursor.execute('''
            SELECT DISTINCT name 
            FROM skus 
            WHERE name IS NOT NULL
        ''')
        
        # 收集所有可能的品牌名
        brand_names = set()
        skipped_names = set()
        
        for (name,) in cursor.fetchall():
            brand = extract_brand_name(name)
            if brand and len(brand) >= 2:  # 忽略太短的品牌名
                brand_names.add(brand)
            else:
                skipped_names.add(name)
        
        print(f"\n发现 {len(brand_names)} 个可能的品牌名:")
        for brand in sorted(brand_names):
            print(f"- {brand}")
        
        print(f"\n跳过 {len(skipped_names)} 个无法解析的商品名:")
        for name in sorted(skipped_names):
            print(f"- {name}")
        
        # 确认是否继续
        confirm = input("\n是否继续更新品牌数据？(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return
        
        # 开始事务
        cursor.execute("BEGIN")
        
        try:
            # 创建临时品牌表
            cursor.execute('''
                CREATE TEMP TABLE new_brands (
                    name TEXT PRIMARY KEY,
                    keywords TEXT
                )
            ''')
            
            # 插入新品牌
            for brand in brand_names:
                cursor.execute('''
                    INSERT OR IGNORE INTO new_brands (name, keywords)
                    VALUES (?, ?)
                ''', (brand, brand))
            
            # 插入到正式品牌表
            cursor.execute('''
                INSERT OR IGNORE INTO brands (name, keywords)
                SELECT name, keywords FROM new_brands
            ''')
            
            # 获取品牌ID映射
            cursor.execute('''
                SELECT id, name FROM brands
                WHERE name IN (
                    SELECT DISTINCT substr(s.name, 1, instr(s.name || ' ', ' ') - 1)
                    FROM skus s
                )
            ''')
            brand_map = {name.upper(): id for id, name in cursor.fetchall()}
            
            # 更新商品的品牌ID
            updated = 0
            skipped = 0
            
            cursor.execute('SELECT id, name FROM c2c_items')
            for item_id, name in cursor.fetchall():
                brand = extract_brand_name(name)
                if brand and brand in brand_map:
                    cursor.execute('''
                        UPDATE c2c_items 
                        SET brand_id = ? 
                        WHERE id = ?
                    ''', (brand_map[brand], item_id))
                    updated += 1
                else:
                    skipped += 1
            
            conn.commit()
            
            print(f"\n更新完成!")
            print(f"- 添加了 {len(brand_names)} 个新品牌")
            print(f"- 更新了 {updated} 个商品的品牌")
            print(f"- 跳过了 {skipped} 个商品")
            
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
    update_brands() 