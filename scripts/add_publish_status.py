import sqlite3

def add_publish_status_field():
    """添加商品发布状态字段"""
    try:
        conn = sqlite3.connect('./db/bilibili_mall.db')
        cursor = conn.cursor()
        
        print("开始添加 publish_status 字段...")
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(c2c_items)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'publish_status' not in columns:
            print("添加 publish_status 字段...")
            cursor.execute('''
                ALTER TABLE c2c_items 
                ADD COLUMN publish_status INTEGER DEFAULT 1
            ''')
            conn.commit()
            print("✓ 字段添加成功")
            
            # 更新现有数据
            print("更新现有数据的状态...")
            cursor.execute('''
                UPDATE c2c_items 
                SET publish_status = 1 
                WHERE publish_status IS NULL
            ''')
            rows_updated = cursor.rowcount
            conn.commit()
            print(f"✓ 更新了 {rows_updated} 条记录")
            
        else:
            print("! publish_status 字段已存在，无需添加")
        
        print("\n数据库更新完成!")
        
    except Exception as e:
        print(f"发生错误: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_publish_status_field() 