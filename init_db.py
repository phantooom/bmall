import sqlite3
import os

def init_db():
    """初始化数据库"""
    # 确保数据库目录存在
    os.makedirs('./db', exist_ok=True)
    
    # 连接数据库
    conn = sqlite3.connect('./db/bilibili_mall.db')
    cursor = conn.cursor()
    
    try:
        # 开启外键约束
        cursor.execute('PRAGMA foreign_keys = ON')
        
        # 创建品牌表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            keywords TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建SKU主表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS skus (
            sku_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            img TEXT,
            market_price REAL,
            type INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建商品主表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS c2c_items (
            id INTEGER PRIMARY KEY,
            type INTEGER,
            name TEXT,
            brand_id INTEGER,
            sku_id INTEGER,
            items_id INTEGER,
            total_items_count INTEGER,
            price REAL,
            show_price TEXT,
            show_market_price TEXT,
            uid TEXT,
            payment_time INTEGER,
            is_my_publish INTEGER,
            uspace_jump_url TEXT,
            uface TEXT,
            uname TEXT,
            publish_status INTEGER DEFAULT 1,
            is_blacklisted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_check_time TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands(id),
            FOREIGN KEY (sku_id) REFERENCES skus(sku_id)
        )
        ''')
        
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
        
        # 添加索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_id ON c2c_items(id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_sku_id ON c2c_items(sku_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_items_id ON c2c_items(items_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_brand_id ON c2c_items(brand_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_uid ON c2c_items(uid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_created_at ON c2c_items(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_last_check_time ON c2c_items(last_check_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_c2c_items_publish_status ON c2c_items(publish_status)')
        
        # 初始化品牌数据
        brands = [
            ('TAITO', 'TAITO|タイトー|太东'),
            ('SEGA', 'SEGA|世嘉|セガ'),
            ('BANPRESTO', 'BANPRESTO|万代南梦宫|バンプレスト'),
            ('FURYU', 'FURYU|フリュー|福龙'),
            ('BANDAI', 'BANDAI|万代|バンダイ'),
            ('GOODSMILE', 'GOODSMILE|GSC|굿스마일|グッドスマイル'),
            ('ALTER', 'ALTER|阿尔塔|アルター'),
            ('KOTOBUKIYA', 'KOTOBUKIYA|寿屋|コトブキヤ'),
            ('ANIPLEX', 'ANIPLEX|アニプレックス'),
            ('HOBBY STOCK', 'HOBBY STOCK|ホビーストック'),
            ('KADOKAWA', 'KADOKAWA|角川|カドカワ'),
            ('WAVE', 'WAVE|ウェーブ'),
            ('BROCCOLI', 'BROCCOLI|ブロッコリー'),
            ('AQUAMARINE', 'AQUAMARINE|アクアマリン'),
            ('MEDICOS', 'MEDICOS|メディコス'),
            ('MEGAHOUSE', 'MEGAHOUSE|メガハウス'),
            ('ORANGE ROUGE', 'ORANGE ROUGE|オランジュ・ルージュ'),
            ('STRONGER', 'STRONGER|ストロンガー'),
        ]
        
        cursor.executemany('''
            INSERT OR IGNORE INTO brands (name, keywords)
            VALUES (?, ?)
        ''', brands)
        
        # 提交事务
        conn.commit()
        print("数据库初始化成功！")
        
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def upgrade_db():
    """升级数据库结构"""
    conn = sqlite3.connect('./db/bilibili_mall.db')
    cursor = conn.cursor()
    
    try:
        # 检查是否需要添加 last_check_time 字段
        cursor.execute("PRAGMA table_info(c2c_items)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'last_check_time' not in columns:
            print("添加 last_check_time 字段...")
            cursor.execute('''
                ALTER TABLE c2c_items
                ADD COLUMN last_check_time TIMESTAMP
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_c2c_items_last_check_time 
                ON c2c_items(last_check_time)
            ''')
        
        conn.commit()
        print("数据库升级完成！")
        
    except Exception as e:
        print(f"升级数据库时出错: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    try:
        init_db()
    except sqlite3.OperationalError as e:
        if "no such column: last_check_time" in str(e):
            print("检测到需要升级数据库...")
            upgrade_db()
            print("重新初始化数据库...")
            init_db()
        else:
            raise 