import sqlite3

def add_check_time_field():
    """添加最后检查时间字段"""
    try:
        conn = sqlite3.connect('./db/bilibili_mall.db')
        cursor = conn.cursor()
        
        print("开始添加 last_check_time 字段...")
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(c2c_items)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_check_time' not in columns:
            print("添加 last_check_time 字段...")
            cursor.execute('''
                ALTER TABLE c2c_items 
                ADD COLUMN last_check_time TIMESTAMP NULL
            ''')
            conn.commit()
            print("✓ 字段添加成功")
            
        else:
            print("! last_check_time 字段已存在，无需添加")
        
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
    add_check_time_field() 